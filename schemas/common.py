"""
Schemas comunes y reutilizables
Define modelos base, tipos comunes y respuestas estándar que se usan en múltiples endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from enum import Enum


# ============================================
# Enums comunes
# ============================================

class EstadoRespuesta(str, Enum):
    """Estados posibles de una respuesta API"""
    EXITO = "exito"
    ERROR = "error"
    PENDIENTE = "pendiente"
    PROCESANDO = "procesando"


class TipoError(str, Enum):
    """Tipos de error comunes"""
    VALIDACION = "validacion"
    CONEXION = "conexion"
    AUTENTICACION = "autenticacion"
    SERVICIO = "servicio"
    DATOS = "datos"
    GENERAL = "general"


# ============================================
# Modelos de respuesta estándar
# ============================================

class ErrorResponse(BaseModel):
    """
    Modelo estándar para respuestas de error.
    Usado en todos los endpoints para mantener consistencia.
    """
    estado: Literal["error"] = "error"
    mensaje: str = Field(..., description="Mensaje de error amigable para el cliente")
    detalles_usuario: Optional[str] = Field(None, description="Detalles adicionales del error para el usuario")
    codigo_error: Optional[str] = Field(None, description="Código de error interno para debugging")
    tipo_error: Optional[TipoError] = Field(None, description="Categoría del error")


class SuccessResponse(BaseModel):
    """
    Modelo estándar para respuestas exitosas simples.
    """
    estado: Literal["exito"] = "exito"
    mensaje: str = Field(..., description="Mensaje de éxito para el cliente")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de respuesta adicionales")


class PaginatedResponse(BaseModel):
    """
    Modelo estándar para respuestas paginadas.
    """
    data: List[Any] = Field(default_factory=list, description="Datos de la página actual")
    total: int = Field(..., description="Total de elementos")
    page: int = Field(1, ge=1, description="Página actual")
    page_size: int = Field(10, ge=1, le=100, description="Tamaño de página")
    total_pages: int = Field(..., description="Total de páginas")


class StatusResponse(BaseModel):
    """
    Modelo para respuestas de estado de operaciones.
    """
    estado: EstadoRespuesta
    mensaje: str
    progreso: Optional[float] = Field(None, ge=0, le=100, description="Porcentaje de progreso (0-100)")
    detalles: Optional[Dict[str, Any]] = None


# ============================================
# Modelos base reutilizables
# ============================================

class BaseClientRequest(BaseModel):
    """
    Modelo base para requests que incluyen un ID de cliente.
    """
    client_id: str = Field(..., min_length=1, description="ID del cliente")


class BaseTimestampModel(BaseModel):
    """
    Modelo base con campos de timestamp.
    """
    created_at: Optional[str] = Field(None, description="Fecha de creación ISO 8601")
    updated_at: Optional[str] = Field(None, description="Fecha de última actualización ISO 8601")


class MetadataModel(BaseModel):
    """
    Modelo para metadatos adicionales genéricos.
    """
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[str] = Field(None, description="Origen de la request (web, mobile, api)")
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    extra: Optional[Dict[str, Any]] = Field(None, description="Datos extra personalizados")


# ============================================
# Tipos comunes
# ============================================

# Type alias para IDs
ClientID = str
PayableID = str
CreditLineID = str
TransactionID = str

# Type alias para responses
APIResponse = Dict[str, Any]
