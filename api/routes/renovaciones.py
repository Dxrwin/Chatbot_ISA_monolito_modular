"""
Rutas de API para Renovaciones de Crédito.

Este módulo contiene los endpoints REST para el flujo de renovaciones
de crédito con relación padre-hijo entre tablas.
"""
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import aiomysql

from schemas.webhooks import RenovacionClienteRequest
from utils.database import insertar_renovacion_vinculada

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/registrar-renovacion",
    status_code=status.HTTP_201_CREATED,
    summary="Registrar renovación de crédito vinculada",
    description="Inserta un registro de renovación de crédito con relación transaccional "
                "entre las tablas credito (padre) y renovaciones_clientes (hija).",
    tags=["Renovaciones"],
    response_description="Renovación registrada exitosamente con IDs generados"
)
async def registrar_renovacion_endpoint(payload: RenovacionClienteRequest):
    """
    Endpoint para registrar una renovación de crédito de forma transaccional.
    
    Flujo:
    1. Valida el request con Pydantic (datos del cliente + datos del crédito)
    2. Mapea el estado numérico a texto automáticamente
    3. Inserta en tabla 'credito' (padre)
    4. Inserta en tabla 'renovaciones_clientes' (hija) con FK
    5. Ejecuta commit o rollback según el resultado
    
    Args:
        payload: RenovacionClienteRequest con datos del cliente y crédito anidados
    
    Returns:
        JSONResponse con código 201 y los IDs generados
    
    Raises:
        HTTPException 400: Estado de crédito inválido
        HTTPException 500: Error de base de datos o transacción
    """
    method_name = "registrar_renovacion_endpoint"
    
    try:
        logger.info(
            f"[{method_name}] Recibiendo solicitud de renovación | "
            f"Cliente: {payload.nombre_cliente} | ID_Credito: {payload.ID_Credito_simulacion}"
        )
        
        # Preparar datos para la función de servicio
        renovacion_data = {
            "ID_Credito_simulacion": payload.ID_Credito_simulacion,
            "numero_telefono": payload.numero_telefono,
            "correo_cliente": payload.correo_cliente,
            "nombre_cliente": payload.nombre_cliente,
            "credito_data": payload.credito_data.model_dump(),
        }
        
        # Llamar a la función de servicio que maneja la transacción
        id_credito, id_renovacion = await insertar_renovacion_vinculada(renovacion_data)
        
        logger.info(
            f"[{method_name}] Renovación registrada exitosamente | "
            f"ID_Credito: {id_credito} | ID_Renovacion: {id_renovacion}"
        )
        
        # Respuesta exitosa
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message": "Renovación de crédito registrada exitosamente",
                "data": {
                    "id_credito_simulacion": id_credito,
                    "id_renovacion_cliente": id_renovacion,
                    "nombre_cliente": payload.nombre_cliente,
                    "estado_credito": payload.credito_data.estado_credito_post_confirmado,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    except ValueError as ve:
        # Error de validación de estado
        logger.warning(
            f"[{method_name}] Estado de crédito inválido | Error: {str(ve)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Estado de crédito inválido",
                "message": str(ve),
                "cliente": payload.nombre_cliente,
            },
        )
    
    except aiomysql.Error as db_error:
        # Error de base de datos
        logger.error(
            f"[{method_name}] Error de base de datos | Error: {str(db_error)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Error de base de datos",
                "message": "No se pudo completar la transacción. Los cambios fueron revertidos.",
                "cliente": payload.nombre_cliente,
            },
        )
    
    except Exception as e:
        # Error genérico
        logger.error(
            f"[{method_name}] Error inesperado | Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Error interno del servidor",
                "message": "Ocurrió un error inesperado al procesar la solicitud",
                "detail": str(e),
            },
        )
