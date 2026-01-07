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
    Crea un payable usando el cliente modular de Kuenta.
    Maneja creación + simulación en un flujo lineal.
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
    Consulta estado usando el cliente modular.
    Sigue intentando hasta 3 veces si el estado es 'pending',
    pero usa la lógica limpia del cliente para la petición HTTP.
    """
    method_name = "obtener_estado"
    creditid = payload.get("creditid")
    orderid = payload.get("orderid")
    
    if not creditid or not orderid:
        raise HTTPException(status_code=400, detail="Faltan creditid u orderid")

    async with httpx.AsyncClient() as auth_client:
        token = await obtener_token(auth_client)

    if not token:
        raise HTTPException(status_code=401, detail="Error de autenticación interna")

    intentos = 3
    intervalo = 10
    
    try:
        # Bucle de lógica de negocio (polling), no de conexión HTTP
        for i in range(intentos):
            try:
                data = await get_payment_status(
                    access_token=token,
                    org_id=ORG_ID,
                    client_id=debtor_id,
                    credit_id=creditid,
                    order_id=orderid
                )
                
                status = data.get("status")
                logger.info(f"Intento {i+1}: status = {status}")
                
                if status != "pending":
                    return data
                
                if i < intentos - 1:
                    await asyncio.sleep(intervalo)
                    
            except KuentaAPIError as e:
                logger.error(f"Error consultando estado (Intento {i+1}): {e}")
                # Si falla la API, podemos decidir si parar o seguir
                if i == intentos - 1:
                    raise HTTPException(status_code=502, detail="Error consultando estado en Kuenta")

        return {"mensaje": "No se obtuvo estado final tras intentos", "status": "pending"}

    except Exception as e:
        logger.error(f"Error general en obtener_estado: {e}")
        await error_notify(method_name, debtor_id, str(e))
        raise HTTPException(status_code=500, detail="Error procesando la solicitud")
