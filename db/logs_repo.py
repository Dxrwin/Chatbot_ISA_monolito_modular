"""
Repositorio para la gestión de logs en base de datos.
"""
import logging
import aiomysql
from typing import Optional, Dict, Any
from db.connection import get_pool

logger = logging.getLogger(__name__)

async def insertar_log(
    method_name: str,
    client_id: Optional[str] = None,
    error_message: Optional[str] = None,
    http_code: Optional[int] = None,
    tipo: str = "error",
    nombre_archivo: Optional[str] = None,
    numero_linea: Optional[int] = None,
    traceback_str: Optional[str] = None,
    respuesta_api: Optional[str] = None,
    payload_enviado: Optional[str] = None
) -> bool:
    """
    Inserta un registro de auditoría.
    Retorna True si fue exitoso, False si falló (pero no lanza excepción).
    """
    query = """
        INSERT INTO logs (
            method_name, client_id, error_message, http_code, tipo, 
            nombre_archivo, numero_linea, traceback, respuesta_api, 
            payload_enviado, timestamp
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    params = (
        method_name, 
        str(client_id)[:255] if client_id else None,
        error_message, http_code, tipo, nombre_archivo, numero_linea,
        traceback_str, respuesta_api, payload_enviado
    )
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                await conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error crítico al insertar log en BD: {e}")
        return False

async def consultar_logs_filtrados(filtros: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consulta dinámica de logs para el panel administrativo.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = "SELECT * FROM logs WHERE 1=1"
                params = []
                
                # Filtros opcionales
                if filtros.get("log_id"):
                    query += " AND id = %s"
                    params.append(filtros["log_id"])
                
                if filtros.get("metodo"):
                    query += " AND method_name LIKE %s"
                    params.append(f"%{filtros['metodo']}%")
                
                if filtros.get("client_id"):
                    query += " AND client_id LIKE %s"
                    params.append(f"%{filtros['client_id']}%")
                
                if filtros.get("tipo"):
                    query += " AND tipo = %s"
                    params.append(filtros["tipo"])

                # Paginación
                query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
                params.extend([filtros.get("limite", 100), filtros.get("offset", 0)])
                
                await cursor.execute(query, tuple(params))
                registros = await cursor.fetchall()
                
                # Obtener total para paginación
                await cursor.execute("SELECT COUNT(*) as total FROM logs")
                total = await cursor.fetchone()
                
                return {
                    "total": total['total'] if total else 0,
                    "registros": registros
                }
    except Exception as e:
        logger.error(f"Error consultando logs: {e}")
        return {"error": str(e), "registros": []}