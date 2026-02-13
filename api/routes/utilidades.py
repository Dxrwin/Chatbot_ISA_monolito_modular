from fastapi import APIRouter, HTTPException
from typing import Optional
from services.utilidades import formatear_valores_service

router = APIRouter(prefix="/utilidades", tags=["Utilidades"])

@router.get("/formatear")
async def formatear_valores(valor: Optional[str] = None, fecha: Optional[str] = None):
    """Procesa valores y fechas."""
    if not valor and not fecha:
        raise HTTPException(status_code=400, detail="Debe enviar 'valor' o 'fecha'")
        
    return await formatear_valores_service(valor, fecha)