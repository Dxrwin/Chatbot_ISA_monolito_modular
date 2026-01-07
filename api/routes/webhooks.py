from fastapi import APIRouter

from schemas.webhooks import RenovacionPayload, WebhookPayload
from services.renovaciones import registrar_renovacion
from services.webhooks import procesar_webhook

router = APIRouter()


@router.post(
    "/Correo_post_llamada",
    summary="Receptor de variables despues de la llamada",
    description="Recibe el payload con las variables de entrada y extraidas.",
    tags=["Correo_post_llamada"],
)
async def handle_webhook(payload: WebhookPayload):
    return await procesar_webhook(payload)


@router.post("/renovaciones", tags=["Renovaciones"], summary="Registrar renovacion de cliente")
async def registrar_renovacion_endpoint(payload: RenovacionPayload):
    return await registrar_renovacion(payload)
