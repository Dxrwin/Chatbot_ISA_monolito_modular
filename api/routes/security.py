from fastapi import APIRouter, Header, HTTPException
from schemas.security import ConfirmarTOTPRequest
from services.security import confirmar_totp_service

router = APIRouter(prefix="/security", tags=["Seguridad"])

@router.post("/confirmar-totp")
async def confirmar_totp(payload: ConfirmarTOTPRequest, authorization: str = Header(None)):
    # Simple wrapper que llama al servicio
    result = await confirmar_totp_service(payload, authorization)
    
    if result.get("status") != 200:
        raise HTTPException(status_code=result.get("status"), detail=result)
        
    return result