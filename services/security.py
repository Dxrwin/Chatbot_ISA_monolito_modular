import logging
from typing import Dict, Any
from schemas.security import ConfirmarTOTPRequest
from utils.auth import obtener_token
from utils.notify_error import info_notify
from core.config import settings
from clients import kuenta

logger = logging.getLogger(__name__)

ERRORES_TOTP = {
    "InvalidRequest": "El código TOTP es inválido.",
    "ExpiredCode": "El código ha expirado.",
    "MaxAttemptsExceeded": "Has excedido el número máximo de intentos.",
    "UserNotFound": "No se encontró el usuario.",
    "UnauthorizedRequest": "No tienes permiso para realizar esta acción."
}

async def confirmar_totp_service(request: ConfirmarTOTPRequest) -> Dict[str, Any]:
    """
    Servicio para validación TOTP. 
    Delega la conexión HTTP a clients.kuenta.approve_totp.
    """
    client_id = request.id_debtor
    method_name = "confirmar_totp"
    
    try:
        token = await obtener_token()
        
        # Llamada a la capa de cliente
        # clients.kuenta ya usa ExternalClient internamente con sus reintentos
        response = await kuenta.approve_totp(
            access_token=token,
            org_id=settings.ORG_ID,
            id_debtor=request.id_debtor,
            id_asistance=request.id_asistance,
            codigo=request.codigo_totp
        )
        
        status_code = response.get("status")
        data = response.get("data", {})
        
        # 1. Éxito
        if status_code == 200 and data.get("status") == "success":
            await info_notify(method_name, client_id, "TOTP confirmado exitosamente")
            return {"success": True, "data": data}

        # 2. Errores de Negocio (400, 412, etc o 200 con status fail)
        error_code = data.get("data", {}).get("code")
        
        # Mapeo de errores amigables
        mensaje = ERRORES_TOTP.get(error_code, "Error al verificar código")
        
        return {
            "success": False,
            "status": 400 if status_code < 500 else 500,
            "error": mensaje,
            "raw_error": error_code,
            "detail": data
        }

    except Exception as e:
        logger.error(f"Error crítico en servicio TOTP: {e}", exc_info=True)
        return {"success": False, "status": 500, "error": "Error interno del servidor"}