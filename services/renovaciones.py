import logging
from datetime import datetime, timezone

import aiomysql
from fastapi.responses import JSONResponse

from db.connection import get_pool
from db.renovaciones_repo import insert_renovacion, exists_renovacion
from schemas.webhooks import RenovacionPayload
from utils.notify_error import error_notify, info_notify

logger = logging.getLogger(__name__)


async def registrar_renovacion(payload: RenovacionPayload):
    """
    Caso de uso para registrar una renovacion de credito en la base de datos.
    """
    method_name = "registrar_renovacion"

    try:
        logger.info(f"Intentando registrar renovacion para: {payload.nombre_cliente}")

        pool = await get_pool()
        doc_or_phone = getattr(payload, "documento", None) or getattr(payload, "telefono", None)

        if doc_or_phone and await exists_renovacion(pool, doc_or_phone):
            info_message = (
                "Renovacion ya registrada (idempotente)\n"
                f"Cliente: {payload.nombre_cliente}\n"
                f"Documento/Telefono: {doc_or_phone}"
            )
            await info_notify(
                method_name=method_name,
                client_id=payload.nombre_cliente,
                info_message=info_message,
            )
            return JSONResponse(
                status_code=200,
                content={
                    "status": "exists",
                    "message": "Renovacion ya registrada",
                    "cliente": payload.nombre_cliente,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        insertado_id = await insert_renovacion(
            pool,
            {
                "estado_final_renovacion": payload.estado_final_renovacion,
                "estado_pago_payvalida": payload.estado_pago_payvalida,
                "nombre_cliente": payload.nombre_cliente,
            },
        )

        info_message = (
            "Renovacion registrada exitosamente en la base de datos\n"
            f"Cliente: {payload.nombre_cliente}\n"
            f"Estado Final: {payload.estado_final_renovacion}\n"
            f"Estado Pago: {payload.estado_pago_payvalida}\n"
            f"ID Registro: {insertado_id}"
        )

        await info_notify(
            method_name=method_name,
            client_id=payload.nombre_cliente,
            info_message=info_message,
            entity_id=str(insertado_id),
        )

        return JSONResponse(
            status_code=201,
            content={
                "status": "success",
                "message": "Renovacion registrada exitosamente",
                "id_registro": insertado_id,
                "cliente": payload.nombre_cliente,
                "estado_final_renovacion": payload.estado_final_renovacion,
                "estado_pago_payvalida": payload.estado_pago_payvalida,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    except aiomysql.Error as db_error:
        logger.error(f"Error de base de datos: {str(db_error)}")
        await error_notify(
            method_name=method_name,
            client_id=payload.nombre_cliente,
            error_message=f"Error al insertar en BD: {str(db_error)}",
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error al conectar con la base de datos",
                "detail": "No se pudo registrar la renovacion",
            },
        )

    except Exception as e:
        logger.error(f"Error en registrar_renovacion: {str(e)}")
        await error_notify(
            method_name=method_name,
            client_id=payload.nombre_cliente,
            error_message=f"Error en registrar_renovacion: {str(e)}",
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Error interno del servidor",
                "detail": str(e),
            },
        )
