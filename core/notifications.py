"""
Módulo de notificaciones - Interfaz unificada
Proporciona una capa de abstracción sobre el sistema de notificaciones
para separar la lógica de servicios de la implementación de notificaciones.
"""
from typing import Optional
from utils.notify_error import info_notify as _info_notify, error_notify as _error_notify


async def notify_info(msg: str, **meta) -> None:
    """
    Envía una notificación informativa.
    
    Args:
        msg: Mensaje informativo a enviar
        **meta: Metadatos adicionales como method_name, client_id, entity_id, etc.
    
    Ejemplo:
        await notify_info(
            "Servidor iniciado correctamente",
            method_name="startup_server",
            client_id="system"
        )
    """
    method_name = meta.get("method_name", "unknown_method")
    client_id = meta.get("client_id", "unknown_client")
    entity_id = meta.get("entity_id", None)
    
    await _info_notify(
        method_name=method_name,
        client_id=client_id,
        info_message=msg,
        entity_id=entity_id
    )


async def notify_error(msg: str, exc: Optional[Exception] = None, **meta) -> None:
    """
    Envía una notificación de error.
    
    Args:
        msg: Mensaje de error a enviar
        exc: Excepción opcional asociada al error
        **meta: Metadatos adicionales como method_name, client_id, etc.
    
    Ejemplo:
        await notify_error(
            "No se pudo conectar a la base de datos",
            exc=e,
            method_name="database_connect",
            client_id="12345"
        )
    """
    method_name = meta.get("method_name", "unknown_method")
    client_id = meta.get("client_id", "unknown_client")
    
    # Si se proporciona una excepción, incluirla en el mensaje
    if exc:
        error_message = f"{msg}\nExcepción: {str(exc)}"
    else:
        error_message = msg
    
    await _error_notify(
        method_name=method_name,
        client_id=client_id,
        error_message=error_message
    )
