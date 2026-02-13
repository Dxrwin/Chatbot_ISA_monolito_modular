import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from utils.formatters import limpiar_valor_principal

logger = logging.getLogger(__name__)

async def formatear_valores_service(valor: Optional[str], fecha: Optional[str]) -> Dict[str, Any]:
    result = {"procesados": 0}
    
    # Procesar Valor
    if valor:
        try:
            if str(valor).lower() == "now":
                processed = datetime.now(timezone.utc).isoformat()
                tipo = "fecha"
            else:
                processed = await limpiar_valor_principal(valor)
                tipo = "numerico"
            
            result["valor"] = {"original": valor, "tipo": tipo, "valor_procesado": processed}
            result["procesados"] += 1
        except Exception as e:
            result["valor"] = {"original": valor, "error": str(e), "tipo": "error"}

    # Procesar Fecha
    if fecha:
        try:
            if str(fecha).lower() == "now":
                processed = datetime.now(timezone.utc).isoformat()
                tipo = "fecha"
            else:
                # Reutilizamos lógica de limpieza numérica si aplica, o se podría extender
                processed = await limpiar_valor_principal(fecha) 
                tipo = "numerico"
            
            result["fecha"] = {"original": fecha, "tipo": tipo, "valor_procesado": processed}
            result["procesados"] += 1
        except Exception as e:
            result["fecha"] = {"original": fecha, "error": str(e), "tipo": "error"}
            
    return result