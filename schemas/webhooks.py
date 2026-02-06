"""
Esquemas para los payloads de Webhooks (Agentes de voz/IA).
"""
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class InputVariables(BaseModel):
    """Variables de entrada recibidas del proveedor de voz."""
    NOMBRE_TITULAR: Optional[str] = None
    Nombre: Optional[str] = None
    CORREO: Optional[str] = None
    Contacto: Optional[str] = None
    Celular: Optional[str] = None 
    Universidad: Optional[str] = None
    EMAIL: Optional[str] = None
    PHONE_NUMBER: Optional[str] = Field(None, alias="PHONE_NUMBER")
    SEMESTRE: Optional[int] = None
    LINEA_CREDITO: Optional[str] = None
    ESTADO_CREDITO: Optional[str] = None
    CUOTAS_PENDIENTES: Optional[int] = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("Contacto", "Celular", "PHONE_NUMBER", mode="before")
    @classmethod
    def _cast_phone_like_to_str(cls, v: Any) -> Optional[str]:
        """Convierte números a string para evitar errores de validación."""
        if v is None: return None
        return str(v)

class ExtractedVariables(BaseModel):
    """Variables extraídas durante la conversación por la IA."""
    resumen: Optional[str] = None
    comentario_libre: Optional[str] = Field(None, alias="comentarioLibre")
    contesto_llamada: Optional[bool] = Field(None, alias="contestoLlamada")
    calidad_llamada: Optional[str] = Field(None, alias="calidadLlamada")
    mensaje: Optional[str] = None
    correo_cliente: Optional[str] = Field(None, alias="correoCliente")
    primer_name: Optional[str] = Field(None, alias="primerName")
    desicion_correo: Optional[bool] = Field(None, alias="desicionCorreo")
    ambiguedad: Optional[bool] = Field(None, alias="ambigüedad") # Ojo con el caracter especial
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

    model_config = ConfigDict(extra="allow", populate_by_name=True)

class WebhookPayload(BaseModel):
    """Payload principal del webhook."""
    input_variables: InputVariables = Field(default_factory=InputVariables, alias="inputVariables")
    extracted_variables: ExtractedVariables = Field(default_factory=ExtractedVariables, alias="extractedVariables")

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_extracted_variables(cls, data: Any) -> Any:
        """Normaliza extracted_variables si viene vacío o nulo."""
        if isinstance(data, dict):
            extracted = data.get("extractedVariables") or data.get("extracted_variables")
            if isinstance(extracted, list) or extracted is None:
                data["extracted_variables"] = {}
                if "extractedVariables" in data:
                    data["extractedVariables"] = {}
        return data


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


# ============================================
# Modelos para el Flujo de Renovaciones Vinculadas
# ============================================

class CreditoData(BaseModel):
    """
    Modelo anidado que contiene los datos financieros del crédito.
    Este modelo se inserta en la tabla 'credito' (padre).
    """
    referencia_simulacion: Optional[str] = None
    nombre_linea_simulacion: Optional[str] = None
    cuota_inicial_simulacion: Optional[float] = None
    semestre_renovacion: Optional[str] = None
    estado_credito_post_confirmado: int = Field(
        ..., 
        description="Estado numérico del crédito (0-20). Se validará y mapeará a texto automáticamente."
    )
    valor_solicitud_express: Optional[float] = None

    @field_validator("estado_credito_post_confirmado")
    @classmethod
    def validar_estado_es_entero(cls, v: Any) -> int:
        """
        Valida que el estado sea estrictamente un entero.
        """
        if not isinstance(v, int):
            raise ValueError(
                f"estado_credito_post_confirmado debe ser un entero, recibido: {type(v).__name__}"
            )
        return v

    model_config = ConfigDict(extra="forbid")


class RenovacionClienteRequest(BaseModel):
    """
    Modelo principal para registrar una renovación de crédito con relación padre-hijo.
    Contiene los datos del cliente (tabla hija) y el objeto CreditoData (tabla padre).
    """
    # PK de la tabla credito - se usará como FK en renovaciones_clientes
    ID_Credito_simulacion: str = Field(
        ..., 
        min_length=1,
        description="Identificador único del crédito (PK en tabla credito, FK en renovaciones_clientes)"
    )
    
    # Datos del cliente (tabla renovaciones_clientes)
    numero_telefono: str = Field(..., min_length=7, max_length=20)
    correo_cliente: str = Field(..., min_length=3)
    nombre_cliente: str = Field(..., min_length=1, max_length=150)
    
    # Datos del crédito (tabla credito) - objeto anidado
    credito_data: CreditoData = Field(
        ...,
        description="Datos financieros del crédito que se insertarán en la tabla padre"
    )

    @field_validator("correo_cliente")
    @classmethod
    def validar_formato_email(cls, v: str) -> str:
        """
        Validación básica de formato de email.
        """
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("El correo_cliente debe tener un formato válido")
        return v.strip().lower()

    @field_validator("numero_telefono")
    @classmethod
    def validar_formato_telefono(cls, v: str) -> str:
        """
        Limpia y valida el formato del teléfono.
        """
        # Remover espacios y caracteres comunes
        cleaned = v.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not cleaned.isdigit():
            raise ValueError("El numero_telefono debe contener solo dígitos")
        return cleaned

    model_config = ConfigDict(extra="forbid")
