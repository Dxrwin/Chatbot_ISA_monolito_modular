"""
Ejemplos de uso de schemas/common.py
Ejecutar: python test_common_schemas.py
"""
from schemas.common import (
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse,
    StatusResponse,
    EstadoRespuesta,
    TipoError,
    BaseClientRequest,
    MetadataModel
)


def test_error_response():
    """Ejemplo de respuesta de error estándar"""
    print("\n" + "="*60)
    print("TEST 1: ErrorResponse")
    print("="*60)
    
    error = ErrorResponse(
        mensaje="No se pudo procesar la solicitud",
        detalles_usuario="El ID de cliente no existe en el sistema",
        codigo_error="CLIENT_NOT_FOUND",
        tipo_error=TipoError.VALIDACION
    )
    
    print(f"Estado: {error.estado}")
    print(f"Mensaje: {error.mensaje}")
    print(f"Detalles: {error.detalles_usuario}")
    print(f"Código: {error.codigo_error}")
    print(f"Tipo: {error.tipo_error}")
    print(f"\nJSON: {error.model_dump_json(indent=2)}")


def test_success_response():
    """Ejemplo de respuesta exitosa"""
    print("\n" + "="*60)
    print("TEST 2: SuccessResponse")
    print("="*60)
    
    success = SuccessResponse(
        mensaje="Crédito creado exitosamente",
        data={
            "credit_id": "CR123456",
            "amount": 2500000,
            "status": "approved"
        }
    )
    
    print(f"Estado: {success.estado}")
    print(f"Mensaje: {success.mensaje}")
    print(f"Data: {success.data}")
    print(f"\nJSON: {success.model_dump_json(indent=2)}")


def test_paginated_response():
    """Ejemplo de respuesta paginada"""
    print("\n" + "="*60)
    print("TEST 3: PaginatedResponse")
    print("="*60)
    
    paginated = PaginatedResponse(
        data=[
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
            {"id": "3", "name": "Item 3"}
        ],
        total=25,
        page=1,
        page_size=3,
        total_pages=9
    )
    
    print(f"Total items: {paginated.total}")
    print(f"Página actual: {paginated.page}/{paginated.total_pages}")
    print(f"Items en página: {len(paginated.data)}")
    print(f"\nJSON: {paginated.model_dump_json(indent=2)}")


def test_status_response():
    """Ejemplo de respuesta de estado"""
    print("\n" + "="*60)
    print("TEST 4: StatusResponse")
    print("="*60)
    
    status = StatusResponse(
        estado=EstadoRespuesta.PROCESANDO,
        mensaje="Procesando solicitud de crédito",
        progreso=65.5,
        detalles={
            "step": "verificacion_documentos",
            "estimated_time": "2 minutos"
        }
    )
    
    print(f"Estado: {status.estado}")
    print(f"Mensaje: {status.mensaje}")
    print(f"Progreso: {status.progreso}%")
    print(f"Detalles: {status.detalles}")
    print(f"\nJSON: {status.model_dump_json(indent=2)}")


def test_base_client_request():
    """Ejemplo de request con ID de cliente"""
    print("\n" + "="*60)
    print("TEST 5: BaseClientRequest")
    print("="*60)
    
    request = BaseClientRequest(client_id="CLI123456")
    
    print(f"Client ID: {request.client_id}")
    print(f"\nJSON: {request.model_dump_json(indent=2)}")


def test_metadata_model():
    """Ejemplo de metadatos"""
    print("\n" + "="*60)
    print("TEST 6: MetadataModel")
    print("="*60)
    
    metadata = MetadataModel(
        user_id="USR789",
        session_id="SES456",
        source="mobile",
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        extra={
            "device_type": "iPhone",
            "app_version": "2.1.0"
        }
    )
    
    print(f"User ID: {metadata.user_id}")
    print(f"Source: {metadata.source}")
    print(f"IP: {metadata.ip_address}")
    print(f"Extra: {metadata.extra}")
    print(f"\nJSON: {metadata.model_dump_json(indent=2)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRUEBAS DE SCHEMAS COMUNES")
    print("="*60)
    
    test_error_response()
    test_success_response()
    test_paginated_response()
    test_status_response()
    test_base_client_request()
    test_metadata_model()
    
    print("\n" + "="*60)
    print("PRUEBAS COMPLETADAS")
    print("="*60 + "\n")
