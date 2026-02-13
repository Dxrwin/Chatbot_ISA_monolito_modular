import logging
from typing import Dict, Any
from utils.auth import obtener_token
from utils.notify_error import info_notify
from utils.formatters import formatear_fecha_legible, formatear_valor_moneda
from core.config import settings
from clients import kuenta

logger = logging.getLogger(__name__)

async def obtener_pagos_mora_service(id_credito: str) -> Dict[str, Any]:
    method_name = "obtener_pagos_mora"
    try:
        token = await obtener_token()
        
        # 1. Llamada al Cliente
        response = await kuenta.get_receivables(token, settings.ORG_ID, id_credito)
        status_code = response.get("status")
        
        if status_code == 404:
            return {"status": "error", "http_code": 404, "message": "Crédito no encontrado"}
        if status_code != 200:
            return {"status": "error", "http_code": status_code, "detail": response.get("data")}

        # 2. Procesamiento de Datos
        data = response.get("data", {}).get("data", {}).get("credit", {})
        installments = data.get("installments", [])
        summary = data.get("summary", {})

        count_pending = 0
        count_expired = 0
        first_pending = None

        for inst in installments:
            status = inst.get("status")
            if status == 3: # Pendiente
                count_pending += 1
                if not first_pending:
                    first_pending = {
                        "numero_de_cuota": inst.get("number"),
                        "fecha_pago_legible": formatear_fecha_legible(inst.get("date", "")),
                        "valor_total_legible": formatear_valor_moneda(inst.get("payment", 0)),
                        "dias_de_mora": inst.get("debtInterestDays")
                    }
            elif status == 4: # Vencido
                count_expired += 1

        result = {
            "total_cuotas": len(installments),
            "dias_de_atraso": summary.get("debtDays", 0),
            "pendientes_estado_3": count_pending,
            "vencidos_estado_4": count_expired,
            "pago_pendiente": first_pending
        }
        
        await info_notify(method_name, id_credito, f"Consulta Mora Exitosa: {result}")
        return {"status": "success", "data": result}

    except Exception as e:
        logger.error(f"Error servicio cobranzas: {e}")
        return {"status": "error", "http_code": 500, "message": str(e)}