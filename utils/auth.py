import logging
import time
from typing import Optional
import httpx
from utils.config import settings, TOKEN_DATA
from utils.external_client import ExternalClient

logger = logging.getLogger(__name__)

async def obtener_token(client: Optional[httpx.AsyncClient] = None) -> str:
    """
    Obtiene token de autenticación (Auth0/Kuenta) usando configuración dinámica.
    """
    # 1. Verificar caché en memoria
    if TOKEN_DATA.get("access_token") and TOKEN_DATA.get("expires_at", 0) > int(time.time()) + 30:
        return TOKEN_DATA["access_token"]

    try:
        # 2. Intentar cargar configuración desde BD
        ext_client = await ExternalClient.from_code("AUTH_TOKEN")
        
        # Si la URL no venía en BD, usar la de settings
        if not ext_client.url:
            ext_client.set_url(settings.AUTH_URL)
            
        # Si el body no venía, usar el de settings
        if not ext_client.body:
            ext_client.set_body(settings.AUTH_PAYLOAD_PROD)
            
        result = await ext_client.run()
        
        if result["status"] == 200:
            data = result["data"]
            token = data.get("access_token") or data.get("token")
            expires = data.get("expires_in", 3600)
            
            # Guardar en caché
            TOKEN_DATA["access_token"] = token
            TOKEN_DATA["expires_at"] = int(time.time()) + int(expires)
            return token
            
        raise Exception(f"Error obteniendo token: {result['status']}")

    except ValueError:
        # Fallback si no existe en BD (usando httpx directo)
        logger.warning("AUTH_TOKEN no en BD, usando fallback")
        async with httpx.AsyncClient() as local_client:
            resp = await local_client.post(settings.AUTH_URL, json=settings.AUTH_PAYLOAD_PROD)
            data = resp.json()
            return data.get("access_token")