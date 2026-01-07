import logging

from fastapi.responses import JSONResponse

from schemas.webhooks import TestNotifyRequest
from utils.notify_error import (
    error_notify,
    get_cached_logs,
    send_log_email,
    send_log_telegram,
)

logger = logging.getLogger(__name__)


async def health_status() -> dict:
    return {"status": "ok"}


async def get_logs(limit: int = 20) -> dict:
    try:
        logs = await get_cached_logs(limit)
        if not logs:
            return {"count": 0, "logs": []}
        return {"count": len(logs), "logs": logs}
    except Exception as e:
        logger.exception("Error al obtener logs desde la cache")
        return {"count": 0, "logs": []}


async def test_notify(payload: TestNotifyRequest) -> JSONResponse:
    try:
        result = await error_notify(payload.method_name, payload.client_id, payload.message)
        return JSONResponse(status_code=200, content={"status": "ok", "result": result})
    except Exception as e:
        logger.exception("Error en /test-notify")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


async def test_email(payload: TestNotifyRequest) -> JSONResponse:
    try:
        result = await send_log_email(payload.method_name, payload.client_id, payload.message)
        return JSONResponse(status_code=200, content={"status": "ok", "result": result})
    except Exception as e:
        logger.exception("Error en /test-email")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


async def test_telegram(payload: TestNotifyRequest) -> JSONResponse:
    try:
        result = await send_log_telegram(payload.method_name, payload.client_id, payload.message)
        return JSONResponse(status_code=200, content={"status": "ok", "result": result})
    except Exception as e:
        logger.exception("Error en /test-telegram")
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
