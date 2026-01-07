import logging
from typing import Any, Dict

from fastapi.responses import JSONResponse

from schemas.webhooks import WebhookPayload
from utils.enviar_correo_IA import (
    procesar_llamada_renovacion_Y_refinanciamiento,
    procesar_webhook_renovacion,
    procesar_webhook_webinar,
)
from utils.notify_error import error_notify, info_notify

async def procesar_webhook(payload: WebhookPayload) -> Dict[str, Any]:
    """
    Endpoint principal que recibe el payload del webhook.

    1.  Valida automaticamente el payload contra el modelo `WebhookPayload`.
    2.  Llama al servicio `procesar_webhook` para manejar toda la logica.
    3.  Retorna una respuesta JSON.
    """
    try:
        
        logging.debug(f"Payload completo recibido: {payload.model_dump_json(indent=2)} \n")
        
        # logging.info(f"Objetivo extraido: {payload.extracted_variables.objetivo} \n")
        
        # Logica de enrutamiento de el envio de los correos basada en el objetivo de la llamada de cada agente IA
        objetivo = payload.extracted_variables.objetivo
        logging.info(f"Objetivo a procesar: {objetivo}")
        
        if objetivo == "webinar":
            logging.info("El objetivo es 'webinar'. Llamando a procesar_webhook_webinar.")
            
            #empieza aqui
            resultado = await procesar_webhook_webinar(payload)
            
            logging.info(f"Procesamiento completado para webinar: {payload.input_variables.NOMBRE_TITULAR}")
            
            #Validar explicitamente el resultado
            if resultado.get("status") == "error":
                
                logging.info(f"error en la procesamiento del webhook webinar: {resultado.get('message')}")
                await error_notify(
                    method_name="handle_webhook_webinar",
                    client_id=objetivo,
                    error_message=f"Webhook webinar con problemas: {resultado.get('message')}"
                )
                return JSONResponse(status_code=500,
                                    content={
                                        "status": "error",
                                        "message": resultado.get("message", "Error desconocido"),
                                        "correo_enviado": resultado.get("correo_enviado", False),
                                        "intentos": resultado.get("intentos_correo", 0),
                                        "data": resultado
                                    }
                )
            elif resultado.get("status") == "success":   
                
                logging.info(f"Webhook webinar EXITOSO: Correo enviado")
                await info_notify(
                    method_name="webhook_webinar",
                    client_id=objetivo,
                    info_message=f"Webhook de webinar completado exitosamente. Correo enviado en  para {payload.input_variables.NOMBRE_TITULAR}"
                )
                return JSONResponse(status_code=200,
                                    content={
                                        "status": "success",
                                        "message": "Webhook de renovacion procesado",
                                        "correo_enviado": True,
                                        "intentos": resultado.get("intentos_correo"),
                                        "data": resultado,
                                    })
            else:
                logging.warning(f"Webhook webinar con problemas: {resultado}")
                await error_notify(
                    method_name="handle_webhook_webinar",
                    client_id=objetivo,
                    error_message=f"Webhook webinar con problemas: {resultado.get('message')}"
                )
                return {
                    "status": "error" if resultado.get("status") == "error" else "partial",
                    "message": resultado.get("message", "Error desconocido"),
                    "correo_enviado": resultado.get("correo_enviado", False),
                    "intentos": resultado.get("intentos_correo", 0),
                    "data": resultado
                }
        
        elif objetivo == "renovacion":
            logging.info("El objetivo es 'renovacion'. Llamando a procesar_webhook_renovacion.")
            
            
            resultado = await procesar_webhook_renovacion(payload)
            
            
            logging.info(f"Procesamiento completado para renovacion: {payload.input_variables.NOMBRE_TITULAR}")
            
            #Validar explicitamente el resultado
            if resultado.get("status") == "error":
                logging.info(f"error en la procesamiento del webhook renovacion: {resultado.get('message')}")
                await error_notify(method_name="handle_webhook_renovacion",
                                client_id=objetivo,
                                    error_message=f"Webhook renovacion con problemas: {resultado.get('message')}"
                                    )
                return JSONResponse(status_code=500,
                                    content={"status": "error",
                                            "message": resultado.get("message", "Error desconocido")
                                            ,
                                            "correo_enviado": resultado.get("correo_enviado", False),
                                            "intentos": resultado.get("intentos_correo", 0),
                                            "data": resultado
                                            }
                                    )
            elif resultado.get("status") == "success":
                
                logging.info(f"Webhook renovacion EXITOSO: Correo enviado")
                await info_notify(
                    method_name="handle_webhook_renovacion",
                    client_id=objetivo,
                    info_message=f"Webhook de renovacion completado exitosamente. Correo enviado  para {payload.input_variables.NOMBRE_TITULAR}"
                )
                return  JSONResponse( status_code=200,
                content={
                    "status": "success",
                    "message": "Webhook de renovacion procesado exitosamente",
                    "correo_enviado": True,
                    "intentos": resultado.get("intentos_correo"),
                    "data": resultado
                })
            else:
                logging.warning(f"no se encontro el objetivo de la llamada: {resultado}")
                await error_notify(
                    method_name="handle_webhook_renovacion",
                    client_id=objetivo,
                    error_message=f"Webhook renovacion con problemas: {resultado.get('message')}"
                )
                return {
                    "status": "error" if resultado.get("status") == "error" else "partial",
                    "message": resultado.get("message", "Error desconocido"),
                    "correo_enviado": resultado.get("correo_enviado", False),
                    "intentos": resultado.get("intentos_correo", 0),
                    "data": resultado
                }
                
        elif objetivo == "renovacion y refinanciacion":
            logging.info("El objetivo es 'renovacion y refinanciacion'. Llamando a procesar_llamada_renovacion_Y_refinanciamiento.")
            logging.info(f"payload completo recibido: {payload.model_dump_json(indent=2)} \n")
            
            try:
                resultado = await procesar_llamada_renovacion_Y_refinanciamiento(payload)
                
                logging.info(f"Procesamiento completado para renovacion y refinanciacion: {payload.input_variables.NOMBRE_TITULAR}")
                
                # Validar explicitamente el resultado
                if resultado.get("status") == "error":
                    logging.error(f" Error en el procesamiento: {resultado.get('message')}")
                    await error_notify(
                        method_name="handle_webhook_renovacion_refinanciacion",
                        client_id=objetivo,
                        error_message=f"Error en procesamiento de renovacion y refinanciacion: {resultado.get('message')}"
                    )
                    return JSONResponse(
                        status_code=430,
                        content={
                            "status": "error",
                            "message": resultado.get("message", "Error desconocido"),
                            "acciones_ejecutadas": resultado.get("acciones", []),
                            "errores": resultado.get("errores", []),
                            "data": resultado
                        }
                    )
                elif resultado.get("status") == "success":
                    logging.info(f" Procesamiento EXITOSO para renovacion y refinanciacion")
                    await info_notify(
                        method_name="handle_webhook_renovacion_refinanciacion",
                        client_id=objetivo,
                        info_message=f"Procesamiento de renovacion y refinanciacion completado exitosamente para {payload.input_variables.NOMBRE_TITULAR}. Acciones: {', '.join(resultado.get('acciones_ejecutadas', []))}"
                    )
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "success",
                            "message": "Procesamiento de renovacion y refinanciacion completado exitosamente",
                            "cliente": resultado.get("cliente"),
                            "correo": resultado.get("correo"),
                            "acciones_ejecutadas": resultado.get("acciones_ejecutadas", []),
                            "data": resultado
                        }
                    )
                else:
                    # status == "partial" o "warning"
                    logging.warning(f" Procesamiento parcial: {resultado}")
                    await error_notify(
                        method_name="handle_webhook_renovacion_refinanciacion",
                        client_id=objetivo,
                        error_message=f"Procesamiento parcial de renovacion y refinanciacion: {resultado.get('message')}"
                    )
                    return JSONResponse(
                        status_code=430,
                        content={
                            "status": resultado.get("status", "partial"),
                            "message": resultado.get("message", "Procesamiento parcial"),
                            "acciones_ejecutadas": resultado.get("acciones_ejecutadas", []),
                            "errores": resultado.get("errores", []),
                            "data": resultado
                        }
                    )
            except Exception as e:
                logging.error(f" Excepción en procesar_llamada_renovacion_Y_refinanciamiento: {e}", exc_info=True)
                await error_notify(
                    method_name="handle_webhook_renovacion_refinanciacion",
                    client_id=objetivo,
                    error_message=f"Excepción en renovacion y refinanciacion: {str(e)}"
                )
                return JSONResponse(
                    status_code=430,
                    content={
                        "status": "error",
                        "message": f"Error en el procesamiento de renovacion y refinanciacion",
                        "detail": str(e),
                        "cliente": payload.input_variables.NOMBRE_TITULAR if payload and payload.input_variables else "unknown"
                    }
                )

    except Exception as e:
        # No devolver 500 para evitar que el proveedor del webhook reintente
        # y provoque envíos duplicados. Registramos y notificamos, y
        # respondemos 200 con detalle del error interno.
        logging.error(f"Error en el endpoint /webhook: {str(e)}", exc_info=True)
        try:
            await error_notify(
                method_name="handle_webhook",
                client_id=(payload.input_variables.NOMBRE_TITULAR if payload and payload.input_variables else "unknown"),
                error_message=f"Error en el endpoint /webhook: {str(e)}",
            )
        except Exception:
            logging.exception("Fallo al enviar notificacion de error")
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": "Error interno (registrado). No se reintentará desde el servidor.",
                "detail": str(e),
            },
        )


# Endpoint para registrar renovaciones en la base de datos
