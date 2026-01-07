"""
Schemas de Webhooks
Define los modelos de validación para webhooks y requests relacionados.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Any


# ============================================
# Modelos de WebhookPayload (de models.models)
# ============================================

class InputVariables(BaseModel):
    """
    Define la estructura y tipos de las variables de entrada del webhook.
    """
    NOMBRE_TITULAR: Optional[str] = None
    Nombre: Optional[str] = None
    CORREO: Optional[str] = None
    Contacto: Optional[str] = None
    Celular: Optional[str] = None  # Telefono libre usado por el flujo de renovaciones
    Universidad: Optional[str] = None
    EMAIL: Optional[str] = None
    PHONE_NUMBER: Optional[str] = Field(None, alias="PHONE_NUMBER")  # Mapea el alias
    SEMESTRE: Optional[int] = None
    LINEA_CREDITO: Optional[str] = None
    ESTADO_CREDITO: Optional[str] = None
    CUOTAS_PENDIENTES: Optional[int] = None

    # Permite campos adicionales y acepta alias/camelCase
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("Contacto", "Celular", "PHONE_NUMBER", mode="before")
    @classmethod
    def _cast_phone_like_to_str(cls, v: Any) -> Optional[str]:
        """
        Convierte enteros u otros tipos sencillos a str para evitar 422 cuando llegan numeros.
        """
        if v is None:
            return None
        try:
            return str(v)
        except Exception:
            return v


class ExtractedVariables(BaseModel):
    """
    Define la estructura y tipos de las variables extraidas del webhook.
    """
    resumen: Optional[str] = None
    comentario_libre: Optional[str] = Field(None, alias="comentarioLibre")
    contesto_llamada: Optional[bool] = Field(None, alias="contestoLlamada")
    calidad_llamada: Optional[str] = Field(None, alias="calidadLlamada")
    mensaje: Optional[str] = None
    correo_cliente: Optional[str] = Field(None, alias="correoCliente")
    primer_name: Optional[str] = Field(None, alias="primerName")
    desicion_correo: Optional[bool] = Field(None, alias="desicionCorreo")
    ambiguedad: Optional[bool] = Field(None, alias="ambigüedad")
    interes_correo: Optional[str] = Field(None, alias="interesCorreo")
    estado: Optional[bool] = None
    acpt_info_email: Optional[bool] = Field(None, alias="acptInfoEmail")
    aceptoinfocorreo: Optional[str] = Field(None, alias="aceptoInfoCorreo")
    objetivo: Optional[str] = None
    refinanciar: Optional[str] = None
    refinanciar_bool: Optional[bool] = None
    agendo_asst_assr: Optional[str] = Field(None, alias="agendoAsstAssr")
    asst_assr_bool: Optional[bool] = Field(None, alias="asstAssrBool")
    renovacion: Optional[str] = None
    interes_renovar: Optional[str] = None
    envio_correo: Optional[bool] = Field(None, alias="envioCorreo")
    fecha_asst_assor: Optional[str] = Field(None, alias="fechaAsstAssor")
    interessolicitud: Optional[str] = Field(None, alias="interesSolicitud")
    intrsrenovarbool: Optional[bool] = Field(None, alias="intrsRenovarBool")
    
    # Campos adicionales de logica.py
    link_enviado_sms: Optional[str] = None

    # Permite campos adicionales y acepta alias/camelCase
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class WebhookPayload(BaseModel):
    """
    Define la estructura principal del payload que llega al webhook.
    """
    input_variables: InputVariables = Field(default_factory=InputVariables, alias="inputVariables")
    extracted_variables: ExtractedVariables = Field(default_factory=ExtractedVariables, alias="extractedVariables")

    # Permite cualquier otro campo en el nivel superior del payload y alias/camelCase
    model_config = ConfigDict(extra="allow", populate_by_name=True)


# ============================================
# Modelos de Requests adicionales (de logica.py)
# ============================================

class SendEmailRequest(BaseModel):
    """
    Solicitud para enviar correo con variables extraídas.
    """
    extracted_variables: ExtractedVariables
    destinatario: Optional[str] = None  # Email principal (opcional)


class RenovacionPayload(BaseModel):
    """
    Payload para procesar renovaciones.
    """
    estado_final_renovacion: str
    estado_pago_payvalida: str
    nombre_cliente: str


class ClienteRequest(BaseModel):
    """
    Solicitud básica con ID de cliente.
    """
    id_cliente: str


class DetalleCuotaRequest(BaseModel):
    """
    Solicitud para obtener detalle de una cuota específica.
    """
    id_cliente: str
    numero_cuota: int


class TestNotifyRequest(BaseModel):
    """
    Modelo para probar notificaciones.
    """
    method_name: str = "test_method"
    client_id: str = "test_client"
    message: str = "Mensaje de prueba para notificación"
