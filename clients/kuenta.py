"""
Cliente HTTP para Kuenta API
Funciones puras para comunicación con API de Kuenta.
No contiene lógica de negocio, solo HTTP requests, headers, timeouts y parsing JSON.
"""
import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)


# ============================================
# Excepciones personalizadas
# ============================================

class KuentaAPIError(Exception):
    """Excepción base para errores de Kuenta API"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class KuentaConnectionError(KuentaAPIError):
    """Error de conexión o timeout con Kuenta API"""
    pass


class KuentaAuthError(KuentaAPIError):
    """Error de autenticación con Kuenta API"""
    pass


class KuentaNotFoundError(KuentaAPIError):
    """Recurso no encontrado en Kuenta API (404)"""
    pass


class KuentaServerError(KuentaAPIError):
    """Error del servidor de Kuenta (5xx)"""
    pass


# ============================================
# Funciones Helper
# ============================================

def _build_headers(
    access_token: str,
    org_id: str,
    client_id: Optional[str] = None
) -> Dict[str, str]:
    """
    Construye headers estándar para requests a Kuenta API.
    
    Args:
        access_token: Token de autorización
        org_id: ID de la organización
        client_id: ID del cliente (opcional, usado como Organization-ID)
    
    Returns:
        Dict con headers HTTP
    """
    headers = {
        "Config-Organization-ID": org_id,
        "Organization-ID": client_id if client_id else org_id,
        "Authorization": access_token
    }
    return headers


def _handle_http_error(error: httpx.HTTPStatusError) -> None:
    """
    Mapea errores HTTP a excepciones personalizadas.
    
    Args:
        error: Error HTTP de httpx
    
    Raises:
        KuentaAuthError: Para errores 401/403
        KuentaNotFoundError: Para errores 404
        KuentaServerError: Para errores 5xx
        KuentaAPIError: Para otros errores
    """
    status_code = error.response.status_code
    response_text = error.response.text
    
    if status_code in (401, 403):
        raise KuentaAuthError(
            f"Error de autenticación con Kuenta API",
            status_code=status_code,
            response_text=response_text
        )
    elif status_code == 404:
        raise KuentaNotFoundError(
            f"Recurso no encontrado en Kuenta API",
            status_code=status_code,
            response_text=response_text
        )
    elif 500 <= status_code < 600:
        raise KuentaServerError(
            f"Error del servidor de Kuenta",
            status_code=status_code,
            response_text=response_text
        )
    else:
        raise KuentaAPIError(
            f"Error en Kuenta API: {status_code}",
            status_code=status_code,
            response_text=response_text
        )


# ============================================
# Funciones públicas del cliente
# ============================================

async def get_product_lines(access_token: str, org_id: str) -> dict:
    """
    Obtiene líneas de producto desde Kuenta API.
    
    Args:
        access_token: Token de autenticación
        org_id: ID de la organización
    
    Returns:
        Dict con respuesta JSON de la API
    
    Raises:
        KuentaConnectionError: Si hay error de conexión/timeout
        KuentaAPIError: Si hay error en la API
    """
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # segundos base
    TIMEOUT = 15  # segundos
    
    headers = _build_headers(access_token, org_id)
    api_url = settings.API_URL
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"GET {api_url} - Intento {attempt}/{MAX_RETRIES}")
                response = await client.get(api_url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Respuesta exitosa de product lines: {len(data.get('data', {}).get('lines', []))} líneas")
                return data
                
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                logger.warning(f"Intento {attempt}/{MAX_RETRIES} - Error de conexión: {e}")
                
                if attempt == MAX_RETRIES:
                    raise KuentaConnectionError(
                        f"Error de conexión con Kuenta API tras {MAX_RETRIES} intentos",
                        response_text=str(e)
                    )
                
                await asyncio.sleep(RETRY_DELAY * attempt)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
                
                # Para errores 5xx, reintentar
                if 500 <= e.response.status_code < 600 and attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt)
                    continue
                
                _handle_http_error(e)


async def create_payable(
    access_token: str,
    org_id: str,
    client_id: str,
    payload: dict
) -> dict:
    """
    Crea un nuevo payable/crédito en Kuenta.
    
    Args:
        access_token: Token de autenticación
        org_id: ID de la organización
        client_id: ID del cliente
        payload: Datos del payable (dict con creditLineId, principal, etc.)
    
    Returns:
        Dict con respuesta JSON de la API
    
    Raises:
        KuentaConnectionError: Si hay error de conexión
        KuentaAPIError: Si hay error en la API
    """
    MAX_RETRIES = 3
    headers = _build_headers(access_token, org_id, client_id)
    payable_url = settings.PAYABLE_URL
    
    # Filtrar valores None del payload
    clean_payload = {k: v for k, v in payload.items() if v is not None}
    
    async with httpx.AsyncClient() as client:
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"POST {payable_url} - Intento {attempt + 1}/{MAX_RETRIES}")
                logger.debug(f"Payload: {clean_payload}")
                
                response = await client.post(
                    payable_url,
                    json=clean_payload,
                    headers=headers
                )
                
                status_code = response.status_code
                logger.info(f"Intento {attempt + 1}: status_code={status_code}")
                
                if status_code == 201:
                    data = response.json()
                    logger.info("Payable creado exitosamente")
                    return data
                else:
                    logger.error(f"Status code inesperado: {status_code}")
                    logger.error(f"Respuesta: {response.text}")
                    
                    if attempt < MAX_RETRIES - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Reintentando en {wait_time} segundos...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise KuentaAPIError(
                            f"Error al crear payable: status {status_code}",
                            status_code=status_code,
                            response_text=response.text
                        )
                        
            except httpx.HTTPStatusError as e:
                logger.error(f"Intento {attempt + 1}: Error HTTP {e.response.status_code}")
                logger.error(f"Respuesta: {e.response.text}")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    _handle_http_error(e)
                    
            except httpx.RequestError as e:
                logger.error(f"Intento {attempt + 1}: Error de conexión: {str(e)}")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise KuentaConnectionError(
                        f"Error de conexión al crear payable",
                        response_text=str(e)
                    )
    
    # Si llegamos aquí sin retornar, algo salió mal
    raise KuentaAPIError(
        f"No se pudo crear el payable tras {MAX_RETRIES} intentos"
    )


async def get_payable(
    access_token: str,
    org_id: str,
    client_id: str,
    payable_id: str
) -> dict:
    """
    Obtiene detalles de un payable/simulación por ID.
    
    Args:
        access_token: Token de autenticación
        org_id: ID de la organización
        client_id: ID del cliente
        payable_id: ID del payable a consultar
    
    Returns:
        Dict con respuesta JSON de la API
    
    Raises:
        KuentaConnectionError: Si hay error de conexión
        KuentaNotFoundError: Si el payable no existe
        KuentaAPIError: Si hay error en la API
    """
    headers = _build_headers(access_token, org_id, client_id)
    url = f"https://api.kuenta.co/v1/payable/{payable_id}"
    
    try:
        logger.info(f"GET {url}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            status_code = response.status_code
            
            logger.info(f"Status code: {status_code}")
            
            if status_code in (200, 201):
                data = response.json()
                logger.info(f"Payable obtenido exitosamente: {payable_id}")
                return data
            else:
                logger.error(f"Error al obtener payable: {status_code}")
                logger.error(f"Respuesta: {response.text}")
                response.raise_for_status()
                
    except httpx.HTTPStatusError as e:
        logger.error(f"Error HTTP {e.response.status_code}: {e.response.text}")
        _handle_http_error(e)
        
    except httpx.RequestError as e:
        logger.error(f"Error de conexión: {str(e)}")
        raise KuentaConnectionError(
            f"Error de conexión al obtener payable {payable_id}",
            response_text=str(e)
        )


async def get_payment_status(access_token: str, org_id: str, client_id: str, credit_id: str, order_id: str) -> dict:
    """Consulta el estado de una orden de pago específica."""
    headers = _build_headers(access_token, org_id, client_id)
    # Endpoint específico reconstruido
    url = f"https://api.kuenta.co/v1/payable/{credit_id}/installment/0/order/list/{order_id}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            _handle_http_error(e)
        except httpx.RequestError as e:
            raise KuentaConnectionError(f"Error al consultar estado de pago", response_text=str(e))