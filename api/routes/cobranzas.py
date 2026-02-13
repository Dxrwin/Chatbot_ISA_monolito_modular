from fastapi import APIRouter, HTTPException
from schemas.cobranzas import MoraData
from services.cobranzas import obtener_pagos_mora_service

router = APIRouter(prefix="/cobranzas", tags=["Cobranzas"])

@router.post("/pagos-mora")
async def obtener_pagos_mora(payload: MoraData):
    """Obtiene estado de mora de un crédito."""
    res = await obtener_pagos_mora_service(payload.id_credito)
    
    if res["status"] == "error":
        raise HTTPException(status_code=res.get("http_code", 500), detail=res)
        
    return res