from fastapi import APIRouter, Body

from schemas.webhooks import TestNotifyRequest
from services.health import get_logs, health_status, test_email, test_notify, test_telegram

router = APIRouter()


@router.get("/health")
async def health():
    return await health_status()


@router.get("/logs")
async def logs(limit: int = 20):
    return await get_logs(limit)


@router.post("/test-notify")
async def notify(payload: TestNotifyRequest = Body(...)):
    return await test_notify(payload)


@router.post("/test-email")
async def email(payload: TestNotifyRequest = Body(...)):
    return await test_email(payload)


@router.post("/test-telegram")
async def telegram(payload: TestNotifyRequest = Body(...)):
    return await test_telegram(payload)
