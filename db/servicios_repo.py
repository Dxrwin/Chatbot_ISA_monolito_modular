"""
Repositorio para la gestión de la configuración de servicios externos.
"""
import logging
import json
from typing import Optional, Dict, Any
from db.connection import get_pool
import aiomysql

logger = logging.getLogger(__name__)

async def obtener_servicio_externo_por_codigo(codigo: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene la configuración activa de un servicio externo por su código único.
    """
    query = "SELECT * FROM servicios_externos WHERE codigo = %s AND activo = 1 LIMIT 1"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, (codigo,))
                row = await cursor.fetchone()
                
                if row:
                    # Deserializar campos JSON
                    for campo in ['header', 'body']:
                        if isinstance(row.get(campo), str):
                            try:
                                row[campo] = json.loads(row[campo])
                            except:
                                row[campo] = {}
                    return row
        return None
    except Exception as e:
        logger.error(f"Error obteniendo servicio {codigo}: {e}")
        return None

async def crear_servicio_externo(data: Dict[str, Any]) -> int:
    """Inserta una nueva configuración de servicio."""
    query = """
        INSERT INTO servicios_externos 
        (nombre_servicio, codigo, url, metodo, timeout_ms, reintentos, activo, header, body)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    # Serializar JSON para guardado
    header_json = json.dumps(data.get('header')) if data.get('header') else None
    body_json = json.dumps(data.get('body')) if data.get('body') else None
    
    params = (
        data['nombre_servicio'], data['codigo'], data['url'], data.get('metodo', 'POST'),
        data.get('timeout_ms', 10000), data.get('reintentos', 0), data.get('activo', 1),
        header_json, body_json
    )
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            await conn.commit()
            return cursor.lastrowid