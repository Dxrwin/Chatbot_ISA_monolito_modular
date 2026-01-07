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

# Importaciones del cliente modular
from clients.kuenta import (
    create_payable,
    get_payable,
    get_payment_status,
    KuentaAPIError,
    KuentaConnectionError,
    KuentaNotFoundError
)

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
    4. Realiza la peticion POST al endpoint de payable
    
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

            if not token:
                raise HTTPException(status_code=401, detail="No se pudo obtener token de autorización")
            
            # 1) Construimos un payload base con TODOS los campos, incluidos los opcionales
            new_payload = {
                "creditLineId": payload.creditLineId,       
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
            
            try:
                # 3. CREAR PAYABLE (POST)
                logger.info(f"Creando payable para cliente: {client_id}")

                response_data = await create_payable(
                    access_token=token,
                    org_id=ORG_ID,
                    client_id=client_id,
                    payload=new_payload
                )
            
                credit = response_data.get("data", {}).get("credit", {})
                response_credit_id = credit.get("ID")
        
                if not response_credit_id:
                    raise KuentaAPIError("La API no devolvió un ID de crédito válido") 
                
                
            # 4. OBTENER SIMULACIÓN (GET)
                logger.info(f"Consultando simulación para ID: {response_credit_id}")
                simulacion_data = await get_payable(
                    access_token=token,
                    org_id=ORG_ID,
                    client_id=client_id,
                    payable_id=response_credit_id
                )

                # 5. PROCESAR DATOS (Lógica de Negocio Pura)
                credit_data = simulacion_data.get("data", {}).get("credit", {})
                installments = credit_data.get("installments", [])
        
                if not installments:
                    await error_notify(method_name, client_id, "No se encontraron cuotas en la simulación")
                    raise HTTPException(status_code=404, detail="No se encontraron cuotas en la simulación")
                        
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
                    # Cache
                    id_cliente_kuenta = credit_data.get("debtorID")
                    if id_cliente_kuenta and installments:
                        cuotas_cache[id_cliente_kuenta] = {
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
                    # Notificación
                    await info_notify(
                        method_name, 
                        client_id, 
                        f"Crédito {response_credit_id} creado. Total: {formatted_values['payment_formatted']}", 
                        entity_id=str(id_cliente_kuenta)
                    )
                
                    return response_data

                # 6. MANEJO DE ERRORES CENTRALIZADO
                except KuentaConnectionError as e:
                    await error_notify(method_name, client_id, str(e))
                    return JSONResponse(
                        status_code=502,
                        content={
                                        "estado": "error",
                            "mensaje": MENSAJES_CLIENTE["error_conexion"],
                            "detalles_usuario": "Problemas de conexión temporales."
                        }
                    )
                except KuentaNotFoundError as e:
                    await error_notify(method_name, client_id, f"Recurso no encontrado: {str(e)}")
                    raise HTTPException(status_code=404, detail="Recurso no encontrado en Kuenta")

                except KuentaAPIError as e:
                    await error_notify(method_name, client_id, f"Error API: {str(e)}")
                    status = e.status_code or 500
                    return JSONResponse(
                        status_code=status,
                        content={
                            "estado": "error",
                            "mensaje": MENSAJES_CLIENTE["error_servicio"],
                            "detalles_usuario": f"Error del servicio externo ({status})."
                        }
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.exception("Error interno en crear_payable")
                    await error_notify(method_name, client_id, f"Error interno: {str(e)}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "estado": "error",
                            "mensaje": MENSAJES_CLIENTE["error_general"],
                            "detalles_usuario": "Error interno del servidor."
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
