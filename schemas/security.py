"""
Esquemas Pydantic para operaciones de seguridad.
"""
from pydantic import BaseModel

class ConfirmarTOTPRequest(BaseModel):
    """Datos requeridos para validar un código TOTP."""
    codigo_totp: str
    id_debtor: str
    id_asistance: str