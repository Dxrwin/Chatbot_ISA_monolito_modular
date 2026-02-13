from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
from services.simulacion import calcular_financiamiento_service

# Crear el router
router = APIRouter(tags=["Simulacion"])

@router.post("/calcular_financiamiento", summary="Calcular financiamiento de crédito")
async def calcular_financiamiento(payload: Dict[str, Any] = Body(...)):
    """
    Endpoint que recibe los datos del crédito, consulta la línea de producto
    y calcula las cuotas, aval y valores finales.
    """
    # Llamamos al servicio (Lógica de Negocio)
    resultado = await calcular_financiamiento_service(payload)
    
    # Manejo de errores devueltos por el servicio
    if "error" in resultado:
        # Puedes ajustar el código de estado según el tipo de error si tu servicio devuelve códigos
        # Por defecto devolvemos 400 si hay error de negocio, o 500 si es interno
        status_code = 400
        if "interno" in str(resultado.get("error")).lower():
            status_code = 500
            
        raise HTTPException(status_code=status_code, detail=resultado)
        
    return resultado