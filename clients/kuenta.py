"""
Cliente encapsulado para Kuenta.
Utiliza 'ExternalClient' para cargar configuraciones dinámicas desde la base de datos.
"""
import logging
from typing import Dict, Any, Optional
from utils.external_client import ExternalClient
from core.config import settings

logger = logging.getLogger(__name__)

class KuentaAPIError(Exception):
    """Excepción base para errores de API Kuenta."""
    def __init__(self, message: str, status_code: int = 500, response: Any = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

async def get_product_lines(access_token: str, org_id: str, client_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene las líneas de producto.
    Código servicio: KUENTA_LINES_LIST
    """
    try:
        # Cargar configuración desde BD
        client = await ExternalClient.from_code("KUENTA_LINES_LIST", client_id=client_id)
        
        # Inyectar variables dinámicas (URL, Headers)
        client.set_dynamic_values({
            "ORG_ID": org_id,
            "access_token": access_token
        })
        
        # Si la URL no vino de BD, usar fallback (lógica legacy)
        if not client.url:
            client.set_url(f"{settings.API_URL}")

        response = await client.run()
        
        if response["status"] >= 400:
            raise KuentaAPIError("Error obteniendo líneas", response["status"], response["data"])
            
        return response["data"]
        
    except ValueError:
        # Fallback si el servicio no está en BD (Opcional, para compatibilidad)
        raise KuentaAPIError("Servicio KUENTA_LINES_LIST no configurado", 500)

async def get_product_detail(access_token: str, org_id: str, product_id: str) -> Dict[str, Any]:
    """
    Obtiene detalle de un producto (para simulaciones).
    Código servicio: KUENTA_PRODUCT_GET
    """
    client = await ExternalClient.from_code("KUENTA_PRODUCT_GET", client_id=product_id)
    
    client.set_dynamic_values({
        "ORG_ID": org_id,
        "access_token": access_token,
        "linea_producto": product_id
    })
    
    response = await client.run()
    if response["status"] >= 400:
        raise KuentaAPIError(f"Error obteniendo producto {product_id}", response["status"], response["data"])
        
    return response["data"]

async def create_payable(access_token: str, org_id: str, client_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea un crédito (Payable).
    Código servicio: KUENTA_PAYABLE_CREATE
    """
    client = await ExternalClient.from_code("KUENTA_PAYABLE_CREATE", client_id=client_id)
    
    # Inyectar variables: ExternalClient reemplazará {placeholders} en headers Y body
    # Unimos el payload con las variables de contexto para que el reemplazo funcione en ambos lados
    dynamic_context = {
        "ORG_ID": org_id,
        "access_token": access_token,
        **payload # Esparce el payload para reemplazar {principal}, {time}, etc. si están en el body de BD
    }
    
    client.set_dynamic_values(dynamic_context)
    
    # Si el servicio externo NO tiene un body definido en BD, usamos el payload directo
    if not client.body:
        client.set_body(payload)
        
    response = await client.run()
    
    if response["status"] not in [200, 201]:
        raise KuentaAPIError("Error creando payable", response["status"], response["data"])
        
    return response["data"]

async def get_payable(access_token: str, org_id: str, client_id: str, payable_id: str) -> Dict[str, Any]:
    """
    Obtiene la simulación de un payable creado.
    Código servicio: KUENTA_PAYABLE_GET
    """
    client = await ExternalClient.from_code("KUENTA_PAYABLE_GET", client_id=client_id)
    
    # Lógica específica: Añadir ID a la URL si no viene en la plantilla
    base_url = client.url.rstrip("/")
    if "{payable_id}" not in base_url and payable_id not in base_url:
        client.set_url(f"{base_url}/{payable_id}")
    
    client.set_dynamic_values({
        "ORG_ID": org_id,
        "access_token": access_token,
        "payable_id": payable_id
    })
    
    response = await client.run()
    
    if response["status"] != 200:
        raise KuentaAPIError("Error obteniendo simulación", response["status"], response["data"])
        
    return response["data"]

async def confirm_payable(access_token: str, org_id: str, credit_id: str) -> Dict[str, Any]:
    """
    Confirma un crédito (PATCH).
    Código servicio: KUENTA_PAYABLE_CONFIRM
    """
    client = await ExternalClient.from_code("KUENTA_PAYABLE_CONFIRM", client_id=credit_id)
    
    client.set_dynamic_values({
        "ORG_ID": org_id,
        "access_token": access_token,
        "credit_id": credit_id
    })
    
    response = await client.run()
    
    # Retornamos respuesta completa para que el servicio maneje 403 (Token expired) si es necesario
    return response

async def get_order_status(access_token: str, org_id: str, client_id: str, credit_id: str, order_id: str) -> Dict[str, Any]:
    """
    Consulta estado de orden.
    Código servicio: KUENTA_ORDER_STATUS
    """
    client = await ExternalClient.from_code("KUENTA_ORDER_STATUS", client_id=client_id)
    
    # Ajuste de URL si la BD tiene la URL base genérica
    if "{orderid}" not in client.url:
         # Construcción manual similar a logica.py
         client.set_url(f"{client.url.rstrip('/')}/{credit_id}/installments/0/orders/list/{order_id}")

    client.set_dynamic_values({
        "ORG_ID": org_id,
        "access_token": access_token,
        "creditid": credit_id,
        "orderid": order_id
    })
    
    response = await client.run()
    return response

async def approve_totp(access_token: str, org_id: str, id_debtor: str, id_asistance: str, codigo: str) -> Dict[str, Any]:
    """
    Valida código TOTP.
    Código servicio: KUENTA_TOTP_APPROVE
    """
    client = await ExternalClient.from_code("KUENTA_TOTP_APPROVE", client_id=id_debtor)
    
    # Construcción URL específica
    if "assistances" not in client.url:
        base = client.url.rstrip("/")
        client.set_url(f"{base}/{id_debtor}/assistances/{id_asistance}/approve")
        
    client.set_dynamic_values({
        "ORG_ID": org_id,
        "access_token": access_token,
        "codigo_totp": codigo
    })
    
    response = await client.run()
    return response