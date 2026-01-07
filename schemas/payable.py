"""
Schemas de Payable
Define los modelos de validación para operaciones de payable/crédito.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any


class PayableRequest(BaseModel):
    """
    Modelo de solicitud para crear un payable/crédito.
    Incluye validaciones automáticas para transformar strings a tipos numéricos.
    """
    creditLineId: str
    principal: float
    time: int
    paymentFrequency: int
    initialFee: float
    disbursementMethod: Optional[str] = None
    source: Optional[str] = None
    redirectUrl: Optional[str] = None
    callbackUrl: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    @field_validator('principal', 'initialFee', mode='before')
    @classmethod
    def validate_floats(cls, v):
        """
        Convierte strings a float si es necesario.
        Soporta formatos con comas como separador decimal.
        
        Args:
            v: Valor a validar (puede ser str, float, int)
        
        Returns:
            float: Valor convertido a float
        
        Raises:
            ValueError: Si el campo está vacío o no se puede convertir
        """
        if isinstance(v, str):
            if v.strip() == "":
                raise ValueError("El campo no puede estar vacío")
            try:
                return float(v.replace(',', '.').strip())
            except ValueError:
                raise ValueError(f"No se puede convertir '{v}' a número decimal")
        return v

    @field_validator('time', 'paymentFrequency', mode='before')
    @classmethod
    def validate_ints(cls, v):
        """
        Convierte strings a int si es necesario.
        
        Args:
            v: Valor a validar (puede ser str, int)
        
        Returns:
            int: Valor convertido a int
        
        Raises:
            ValueError: Si el campo está vacío o no se puede convertir
        """
        if isinstance(v, str):
            if v.strip() == "":
                raise ValueError("El campo no puede estar vacío")
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"No se puede convertir '{v}' a número entero")
        return v

    @field_validator('disbursementMethod', mode='before')
    @classmethod
    def validate_disbursement(cls, v):
        """
        Valida disbursementMethod, convierte strings vacíos a None.
        
        Args:
            v: Valor a validar
        
        Returns:
            Optional[str]: String válido o None
        """
        if v == "" or v is None:
            return None
        if isinstance(v, str):
            return v.strip() if v.strip() else None
        return v

    @field_validator('creditLineId', mode='before')
    @classmethod
    def validate_creditlineId(cls, v):
        """
        Valida creditLineId, no puede estar vacío.
        
        Args:
            v: Valor a validar
        
        Returns:
            str: creditLineId limpio
        
        Raises:
            ValueError: Si creditLineId está vacío
        """
        if not v or (isinstance(v, str) and v.strip() == ""):
            raise ValueError("creditLineId no puede estar vacío")
        return str(v).strip()
