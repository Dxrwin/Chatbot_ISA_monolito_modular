import logging
from typing import Dict, Any
from utils.auth import obtener_token
from utils.notify_error import error_notify
from core.config import settings
from clients import kuenta  # Usar cliente modular

logger = logging.getLogger(__name__)

async def calcular_financiamiento_service(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lógica de cálculo financiero migrada de logica.py.
    """
    method_name = "calcular_financiamiento"
    linea_producto = payload.get("linea_producto")
    
    try:
        # ... (Validaciones de entrada del monolito: semestre, plazo, etc.) ...
        # ... (Lógica de limpieza de valor principal) ...
        principal = float(str(payload.get("principal", 0)).replace("$","").replace(".","")) # Simplificado para ejemplo
        porcentaje_cuota = float(str(payload.get("porcentaje_cuota", "0")).replace("%", "")) / 100
        
        # Obtener Token
        token = await obtener_token()
        
        # LLAMADA AL CLIENTE REFACTORIZADO (Antes era httpx directo)
        try:
            product_data = await kuenta.get_product_detail(token, settings.ORG_ID, linea_producto)
        except Exception as api_err:
            logger.error(f"Error consultando producto: {api_err}")
            raise ValueError("Error consultando datos del producto en Kuenta")

        # ... (Lógica de validación ID producto) ...
        
        # Cálculo de Aval (Lógica original)
        costs = product_data.get("costs", [])
        aval_cost = next((c for c in costs if c.get("label") == "Aval"), None)
        aval_porcentaje = float(aval_cost.get("percentage", 0)) if aval_cost else 0.0
        
        if (1 - aval_porcentaje) == 0:
            raise ValueError("Porcentaje aval inválido (100%)")

        valor_cuota_inicial = principal * porcentaje_cuota
        valor_desembolsar = principal - valor_cuota_inicial
        valor_solicitar = valor_desembolsar / (1 - aval_porcentaje)
        deducciones = valor_solicitar * aval_porcentaje
        
        return {
            "valor_producto": principal,
            "cuota_inicial": valor_cuota_inicial,
            "valor_solicitado": valor_solicitar,
            "deducciones_anticipadas": deducciones,
            "aval_aplicado_porcentaje": aval_porcentaje,
            # ... formato demostración ...
        }

    except Exception as e:
        logger.error(f"Error cálculo: {e}")
        await error_notify(method_name, str(linea_producto), str(e))
        return {"error": str(e)} # El router manejará el status HTTP