"""
Esquemas Pydantic para la administración del sistema.
Incluye modelos para gestión de logs y configuración de servicios externos.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Modelos para Servicios Externos ---
class ServicioExternoCreateRequest(BaseModel):
    """Modelo para crear una nueva integración externa en BD."""
    nombre_servicio: str
    codigo: str
    url: str
    metodo: str
    timeout_ms: int = 10000
    reintentos: int = 0
    activo: int = 1
    header: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None

class ServicioExternoUpdateRequest(BaseModel):
    """Modelo para actualizar una integración existente."""
    nombre_servicio: Optional[str] = None
    url: Optional[str] = None
    metodo: Optional[str] = None
    timeout_ms: Optional[int] = None
    reintentos: Optional[int] = None
    activo: Optional[int] = None
    header: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None

class ServicioExternoSchema(BaseModel):
    """Schema completo de respuesta para un servicio externo."""
    id: Optional[int] = None
    nombre_servicio: str
    codigo: str
    url: str
    metodo: str
    timeout_ms: int
    reintentos: int
    activo: int
    header: Optional[Dict[str, Any]] = None
    body: Optional[Dict[str, Any]] = None
    creado_en: Optional[str] = None
    actualizado_en: Optional[str] = None

# --- Modelos para Logs ---
class ConsultaLogsRequest(BaseModel):
    """Filtros avanzados para la auditoría de logs."""
    fecha: Optional[str] = None  # Formato D-M-Y
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    log_id: Optional[int] = None
    metodo: Optional[str] = None
    client_id: Optional[str] = None
    codigo_http: Optional[int] = None
    tipo: Optional[str] = None  # "error" o "info"
    limite: int = Field(default=100, le=1000)
    offset: int = 0