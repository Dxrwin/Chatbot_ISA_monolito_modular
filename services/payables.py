import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from core.config import settings
from core.messages import MENSAJES_CLIENTE
from schemas.payable import PayableRequest
from utils.auth import obtener_token
from utils.notify_error import error_notify, info_notify

logger = logging.getLogger(__name__)
ORG_ID = settings.ORG_ID
PAYABLE_URL = settings.PAYABLE_URL
cuotas_cache: Dict[str, Dict[str, Any]] = {}

async def crear_payable(client_id: str, payload: PayableRequest):
    """
    Endpoint para crear un nuevo payable:
    1. Recibe el ID del cliente como parÃƒÂ¡metro
    2. Transforma los campos principal y initialFee de str a int
    3. Extrae el token de autorizacion del payload
    4. Realiza la peticiÃƒÂ³n POST al endpoint de payable
    
    """
    method_name = "create_payable"
    response_credit_id = None
    try:

        async with httpx.AsyncClient() as client:
            
            logger.info(f"+++++ Parámetros recibidos: client_id= {client_id}")
            logger.info(f"#####--- Payload entrante ----####")
            logger.info(f"creditLineId: {payload.creditLineId}")
            logger.info(f"principal: {payload.principal} (tipo: {type(payload.principal).__name__})")
            logger.info(f"time: {payload.time} (tipo: {type(payload.time).__name__})")
            logger.info(f"initialFee: {payload.initialFee} (tipo: {type(payload.initialFee).__name__})")
            logger.info(f"disbursementMethod: {payload.disbursementMethod}")
            logger.info(f"paymentFrequency: {payload.paymentFrequency}")
            
            principal = payload.principal
            initial_fee = payload.initialFee
            
            token = await obtener_token(client)
            
            # 1) Construimos un payload base con TODOS los campos, incluidos los opcionales
            new_payload = {
                "creditLineId": payload.creditLineId,          # ← corregido: antes era creditLineID
                "principal": principal,
                "time": payload.time,
                "disbursementMethod": payload.disbursementMethod,
                "initialFee": initial_fee,
                "paymentFrequency": payload.paymentFrequency,
                # Nuevos campos opcionales según la doc:
                "source": payload.source,
                "redirectUrl": payload.redirectUrl,
                "callbackUrl": payload.callbackUrl,
                "meta": payload.meta,
            }
            
            # 2) Eliminamos solo los que son None para no mandar basura ni nulls innecesarios
            new_payload = {k: v for k, v in new_payload.items() if v is not None}

            logger.info(f"Payload saliente para POST /v1/payable: {new_payload}")
            
            headers = {
                "Config-Organization-ID": ORG_ID,
                "Organization-ID": client_id,
                "Authorization": token
            }
            logger.info(f"Iniciando peticion POST a {PAYABLE_URL}")
            logger.info(f"Payload transformado para enviar a kuenta: {new_payload}")

            max_retries = 3
            for attempt in range(max_retries):
                
                try:
                    response = await client.post(
                        PAYABLE_URL,
                        json=new_payload,
                        headers=headers
                    )
                    status_code = response.status_code
                    
                    logger.info(f"Intento {attempt+1}: status_code={status_code}")
                    
                    if status_code == 201:
                            logger.info("Procesando respuesta de Kuenta")
                            response_data = response.json()
                            credit = response_data.get("data", {}).get("credit", {})
                            
                            #logging.info(f"Respuesta completa de Kuenta: {response_data} \n")
                            
                            # ID credito
                            response_credit_id = credit.get("ID")
                            break  # Salir del bucle de reintentos si fue exitoso
                    else:
                        
                        logger.error(f"Error: Status code no esperado: {status_code}")
                        logger.error(f"Respuesta del servidor: {response.text}")
                        await error_notify(method_name, client_id, f"Error en API externa: status {status_code}")
                        
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.info(f"Reintentando en {wait_time} segundos...")
                            await asyncio.sleep(wait_time)
                
                except httpx.HTTPStatusError as e:
                    logger.error(f"Intento {attempt+1}: Error HTTP {e.response.status_code}")
                    logger.error(f"Respuesta: {e.response.text}")
                    await error_notify(method_name, client_id, f"Error en API externa: {e.response.text}")
                    
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Reintentando en {wait_time} segundos...")
                        await asyncio.sleep(wait_time)
                        
                except httpx.RequestError as e:
                    logger.error(f"Intento {attempt+1}: Error de conexión: {str(e)}")
                    await error_notify(method_name, client_id, 
                        f"Error conexión POST: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Reintentando en {wait_time} segundos...")
                        await asyncio.sleep(wait_time)
            
            # Validar si se obtuvo respuesta exitosa
            if response_credit_id is None:
                logger.error(f"No se logró crear el payable tras {max_retries} intentos")
                await error_notify(method_name, client_id, 
                    f"POST /payable falló tras {max_retries} intentos")
                raise HTTPException(
                    status_code=502,
                    detail=f"Error de conexión tras {max_retries} intentos o respuesta no válida"
                ) 
                
                
            try:
                url_prod = f"https://api.kuenta.co/v1/payable/{response_credit_id}"
                logger.info(f"Consultando simulación: {url_prod}")
                
                response_get_simulacion = await client.get(url_prod, headers=headers)
                status_code_simulacion = response_get_simulacion.status_code
                
                logger.info(f"Status code de la simulación: {status_code_simulacion}")
                            
                            
                if status_code_simulacion == 200 or status_code_simulacion == 201:
                    simulacion_data = response_get_simulacion.json()
                    credit_data = simulacion_data.get("data", {}).get("credit", {})

                    installments = credit_data.get("installments", [])
                    cuota_inicial = credit_data.get("initialFee")
                    ID_credito = credit_data.get("ID")
                    referencia_credito = credit_data.get("reference")
                    id_cliente = credit_data.get("debtorID")


                    if not installments:
                        logger.error("No se encontraron installments en la respuesta")
                        await error_notify(method_name, client_id, 
                            "No se encontraron cuotas en la simulación")
                        raise HTTPException(
                            status_code=404,
                            detail="No se encontraron cuotas en la simulación"
                        )
                        
                    # Tomar el primer installment
                    first_installment = installments[0]
                
                    # Extraer y redondear valores
                    payment = round(float(first_installment.get("payment", 0)))
                    capital = round(float(first_installment.get("capital", 0)))
                    interest = round(float(first_installment.get("interest", 0)))
                    costs = round(float(first_installment.get("costs", 0)))
                    taxes = round(float(first_installment.get("taxes", 0)))
                    # cuota inicial redondeada
                    cuota_inicial_rounded = round(float(cuota_inicial))

                    # Formatear valores para lectura humana
                    formatted_values = {
                        "payment_formatted": f"${payment:,}",
                        "capital_formatted": f"${capital:,}",
                        "interest_formatted": f"${interest:,}",
                        "costs_formatted": f"${costs:,}",
                        "taxes_formatted": f"${taxes:,}",
                        "cuota_inicial_formatted": f"${cuota_inicial_rounded:,}"
                    }

                    # Agregar valores originales y formateados a la respuesta
                    response_data.update({
                        "ID del credito creado": response_credit_id,
                        "valores_originales": {
                            "payment": payment,
                            "capital": capital,
                            "interest": interest,
                            "costs": costs,
                            "taxes": taxes
                        },
                        "valores_formateados": formatted_values
                    })

                    logger.info("Valores extraidos y formateados exitosamente")
                    logger.info(f"Valores formateados: {formatted_values}")
                    # Cacheamos las cuotas simuladas para servirlas rapido en /detalle_cuota_vencida
                    if id_cliente and installments:
                        cuotas_cache[id_cliente] = {
                            "cuotas": installments,
                            "timestamp": datetime.now(timezone.utc)
                        }
                                    
                    # Notificación informativa
                    info_message = (
                        f"Crédito creado y registrado en kuenta correctamente\n"
                        f"ID del crédito: {ID_credito}\n"
                        f"Referencia del crédito: {referencia_credito}\n"
                        f"ID del cliente: {id_cliente}\n"
                        f"Valor total crédito: {formatted_values['payment_formatted']}"
                    )
                                    
                    # envia notificacion informativa (email + telegram) con id para seguimiento
                    await info_notify(method_name, client_id, info_message, entity_id=str(id_cliente))
                
                    return response_data
                else:
                    logger.error(f"Error en la consulta de simulación: {status_code_simulacion}")
                    logger.error(f"Respuesta: {response_get_simulacion.text}")
                    await error_notify(method_name, client_id, 
                        f"Error al consultar simulación: {status_code_simulacion}\nRespuesta: {response_get_simulacion.text}")
                    raise HTTPException(
                        status_code=status_code_simulacion,
                        detail="Error al consultar la simulación"
                    )
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP en GET simulación: {e.response.status_code}")
                logger.error(f"Respuesta: {e.response.text}")
                await error_notify(method_name, client_id, 
                    f"Error en API Kuenta GET: {e.response.status_code}\n{e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error en API externa: {e.response.text}"
                )
                
            except httpx.RequestError as e:
                logger.error(f"Error conexión en GET simulación: {str(e)}")
                await error_notify(method_name, client_id, 
                    f"Error conexión GET: {str(e)}")
                raise HTTPException(
                    status_code=502,
                    detail="Error de conexión al consultar simulación"
                )
                
    except HTTPException:
        raise
        
    except ValueError as e:
        logger.error(f"Error de conversión de datos: {str(e)}")
        await error_notify(method_name, client_id, f"Error de conversión: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_datos"],
                "detalles_usuario": "Recuerda ingresar solo números en los campos de monto y cuota inicial."
            }
        )
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        await error_notify(method_name, client_id, f"Error de conexión: {str(e)}")
        return JSONResponse(
            status_code=502,
            content={
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_conexion"],
                "detalles_usuario": "Nuestro servicio está experimentando problemas de conexión temporales."
            }
        )
        
    except Exception as e:
        logger.error(f"Error interno: {str(e)}", exc_info=True)
        await error_notify(method_name, client_id, f"Error interno: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_general"],
                "detalles_usuario": "Nuestro equipo técnico ha sido notificado y está trabajando en solucionarlo."
            }
        )


async def obtener_estado(debtor_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consulta el estado de un pago con creditid, installmentid y orderid.
    """
    method_name = "obtener_estado"
    creditid = payload.get("creditid")
    installmentid = payload.get("installmentid")
    orderid = payload.get("orderid")
    debtor_id_notify_error = f"debtor_id_cliente = {debtor_id} y creditid = {creditid}"

    try:
        logger.info(f"Parametros recibidos: creditid={creditid}, installmentid={installmentid}, orderid={orderid}")

        if not creditid or not installmentid or not orderid:
            raise HTTPException(
                status_code=400,
                detail="Faltan parametros obligatorios: creditid, installmentid, orderid",
            )

        url = f"https://api.kuenta.co/v1/payable/{creditid}/installment/0/order/list/{orderid}"
        intentos = 3
        intervalo_segundos = 10
        intento = 0

        async with httpx.AsyncClient() as client:
            access_token = await obtener_token(client)
            logger.info(f"Token obtenido: {access_token}")

            if not access_token:
                raise HTTPException(status_code=401, detail="No se pudo obtener el token de acceso")

            headers = {
                "Config-Organization-ID": ORG_ID,
                "Organization-ID": debtor_id,
                "Authorization": access_token,
            }

            while intento < intentos:
                intento += 1
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    status = data.get("status")
                    logger.info(f"Intento {intento}: status del pago = {status}")

                    if status != "pending":
                        logger.info(f"Estado final obtenido: {status} en el intento {intento}")
                        return data

                except Exception as e:
                    logger.error(f"Error en intento {intento}: {str(e)}")
                    await error_notify(
                        method_name, debtor_id_notify_error, f"Error en intento: {intento} {str(e)}"
                    )

                if intento < intentos:
                    await asyncio.sleep(intervalo_segundos)

        return {"mensaje": "No se obtuvo un estado diferente a 'pending' tras 3 intentos"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en el proceso: {str(e)}")
        await error_notify(method_name, debtor_id_notify_error, f"Error en el proceso: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en el proceso: {str(e)}")
