import logging
from typing import Optional, Dict, Any
from datetime import datetime
from utils.auth import obtener_token
from utils.notify_error import error_notify
from core.config import settings
from core.messages import MENSAJES_CLIENTE
import re
import unicodedata

# Importamos el cliente refactorizado
from clients import kuenta

logger = logging.getLogger(__name__)

# funcion para generar un slug a partir del nombre
def slugify_nombre(value: str) -> str:
    if not value: return ""
    normalized = unicodedata.normalize("NFD", value)
    ascii_str = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    ascii_str = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_str)
    ascii_str = re.sub(r"\s+", " ", ascii_str).strip().lower()
    return ascii_str.replace(" ", "-")

async def obtener_product_line(
    parent_id: str,
    name: Optional[str] = None,
    entity_id: Optional[str] = None,
    product_type: Optional[int] = None,
    tipo: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Servicio para buscar y filtrar líneas de producto.
    Usa clients.kuenta.get_product_lines.
    """
    method_name = "obtener_product_line"
    target_slug = slugify_nombre(name) if name else ""
    
    try:
        logger.info(f"[KUENTA_LINES_LIST] Solicitando líneas para parent_id: {parent_id}")
        token = await obtener_token()
        
        # invocamos al cliente que realizara la peticion a la api
        lines_data = await kuenta.get_product_lines(token, settings.ORG_ID, parent_id)
        
        lines = lines_data.get("lines", []) if isinstance(lines_data, dict) else []
        logger.info(f"[KUENTA_LINES_LIST] Líneas obtenidas: {lines}")
        if not lines and isinstance(lines_data, list): lines = lines_data # Manejo si la API devuelve lista directa

        candidates = []
        # ciclo para filtrar las lineas
        for line in lines:
            # si la linea esta archivada, no la consideramos
            if line.get("archived"): continue
            # si la linea no pertenece al entity_id, no la consideramos
            if entity_id and line.get("entityID") != entity_id: continue
            # si el product_type no coincide, no la consideramos
            if product_type is not None and line.get("productType") != product_type: continue
            # si el tipo no coincide, no la consideramos
            if tipo is not None and line.get("type") != tipo: continue

            parent_match = line.get("parentId") == parent_id
            slug_name = slugify_nombre(line.get("name", ""))
            slug_title = slugify_nombre(line.get("title", ""))
            slug_match = bool(target_slug) and (target_slug == slug_name or target_slug == slug_title)

            if parent_match or slug_match:
                candidates.append({"line": line, "matched_by": "parentId" if parent_match else "slug"})
                logger.info(f"Linea encontrada: {line}")

        # Fallback búsqueda parcial
        if not candidates and target_slug:
            for line in lines:
                if line.get("archived"): continue
                slug_name = slugify_nombre(line.get("name", ""))
                slug_title = slugify_nombre(line.get("title", ""))
                if target_slug in slug_name or target_slug in slug_title:
                    candidates.append({"line": line, "matched_by": "partial-slug"})

        if not candidates:
            # Lógica de sugerencias del monolito
            sugerencias = [slugify_nombre(l.get("name", "")) for l in lines][:5]
            return {
                "estado": "error", 
                "mensaje": MENSAJES_CLIENTE["error_servicio"], 
                "sugerencias": sugerencias
            }

        # Ordenamiento
        def parse_updated(val: str):
            try: return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            except: return datetime.min

        candidates.sort(key=lambda x: (parse_updated(x["line"].get("updatedAt")), x["line"].get("version", 0)), reverse=True)
        
        selected = candidates[0]["line"]
        logger.info(f"Linea seleccionada: {selected}")
        #datos de la liena a retornar

        linea_seleccionada = {
            "id": selected.get("id"),
            "name": selected.get("name"),
            "title": selected.get("title"),
            "parentId": selected.get("parentId"),
            "version": selected.get("version"),
            "matched_by": selected["matched_by"],
            "principalMin": selected.get("principalMin"),
            "principalMax": selected.get("principalMax"),
            "timeMin": selected.get("timeMin"),
            "timeMax": selected.get("timeMax"),
            "timeDefault": selected.get("timeDefault"),
            "paymentFrequency": selected.get("paymentFrequency")
        }

        logger.info(f"Linea seleccionada: {linea_seleccionada} \n nombre: {linea_seleccionada.get('name')}\n parentId: {linea_seleccionada.get('parentId')} \n version: {linea_seleccionada.get('version')}\n matched_by: {linea_seleccionada.get('matched_by')}\n principalMin: {linea_seleccionada.get('principalMin')}\n principalMax: {linea_seleccionada.get('principalMax')}\n timeMin: {linea_seleccionada.get('timeMin')}\n timeMax: {linea_seleccionada.get('timeMax')}\n timeDefault: {linea_seleccionada.get('timeDefault')}\n paymentFrequency: {linea_seleccionada.get('paymentFrequency')}")


        return {
            "id": selected.get("id"),
            "name": selected.get("name"),
            "title": selected.get("title"),
            "parentId": selected.get("parentId"),
            "version": selected.get("version"),
            "matched_by": selected["matched_by"],
            "principalMin": selected.get("principalMin"),
            "principalMax": selected.get("principalMax"),
            "timeMin": selected.get("timeMin"),
            "timeMax": selected.get("timeMax"),
            "timeDefault": selected.get("timeDefault"),
            "paymentFrequency": selected.get("paymentFrequency"
            )
        }

    except Exception as e:
        logger.error(f"Error en servicio products: {e}")
        await error_notify(method_name, parent_id, str(e))
        return {"estado": "error", "mensaje": MENSAJES_CLIENTE["error_encontrar_linea"]}
    