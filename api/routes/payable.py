from fastapi import APIRouter, Body, Request

from schemas.payable import PayableRequest
from services.payables import crear_payable_service, obtener_estado_service
from services.simulacion import calcular_financiamiento_service

router = APIRouter()


@router.post("/payable/{client_id}")
async def create_payable(client_id: str, payload: PayableRequest):
    return await crear_payable_service(client_id, payload)


@router.post("/calcular_financiamiento")
async def calcular_financiamiento_endpoint(payload: dict = Body(...)):
    return await calcular_financiamiento_service(payload)


@router.post("/obtener-estado/{debtor_id}")
async def obtener_estado_endpoint(debtor_id: str, request: Request):
    payload = await request.json()
    return await obtener_estado_service(debtor_id, payload)
