import asyncio
import logging
import re
import unicodedata
from datetime import datetime
from typing import Optional

import httpx

from core.config import settings
from core.messages import MENSAJES_CLIENTE
from utils.auth import obtener_token
from utils.notify_error import error_notify

# Importamos el cliente modular
from clients.kuenta import (
    get_product_lines,
    KuentaConnectionError,
    KuentaAPIError
)

logger = logging.getLogger(__name__)
ORG_ID = settings.ORG_ID
API_URL = settings.API_URL


def slugify_nombre(value: str) -> str:
    if not value:
        return ""
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
):
    """
    Recupera una linea de producto desde Kuenta y aplica filtros.
    Busca por parentId y por slug de name/title para soportar cambios de version.
    """

    method_name = "product-lines"
    parent_id_notify_error = f"parent_id para la busqueda de la linea={parent_id}"
    target_slug = slugify_nombre(name) if name else ""

    # Usamos httpx solo para obtener el token (manteniendo la lógica original de auth)
    async with httpx.AsyncClient() as client:
        access_token = await obtener_token(client)
    
    if not access_token:
        await error_notify(method_name, parent_id_notify_error, "No se pudo obtener token")
        return {
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_conexion"],
                "detalles_usuario": "No se pudo obtener el token de acceso.",
        }

    try:
        # 1. LLAMADA AL CLIENTE (Lógica HTTP abstraída)
        data = await get_product_lines(access_token, ORG_ID)
        lines = data.get("data", {}).get("lines", [])
        
        # 2. LÓGICA DE NEGOCIO (Filtrado y Matching)
        candidates = []
        for line in lines:
            if line.get("archived"): continue
            if entity_id and line.get("entityID") != entity_id: continue
            if product_type is not None and line.get("productType") != product_type: continue
            if tipo is not None and line.get("type") != tipo: continue

            parent_match = line.get("parentId") == parent_id
            slug_name = slugify_nombre(line.get("name", ""))
            slug_title = slugify_nombre(line.get("title", ""))
            slug_match = bool(target_slug) and (target_slug == slug_name or target_slug == slug_title)

            if parent_match or slug_match:
                candidates.append({
                    "line": line,
                    "matched_by": "parentId" if parent_match else "slug",
                })

        # Fallback: búsqueda parcial
        if not candidates and target_slug:
            for line in lines:
                if line.get("archived"): continue
                if entity_id and line.get("entityID") != entity_id: continue
                slug_name = slugify_nombre(line.get("name", ""))
                slug_title = slugify_nombre(line.get("title", ""))
                if target_slug in slug_name or target_slug in slug_title:
                    candidates.append({"line": line, "matched_by": "partial-slug"})

        if not candidates:
            sugerencias = [slugify_nombre(l.get("name", "")) for l in lines][:10]
            logger.warning(f"No se encontró línea. Parent: {parent_id}, Slug: {target_slug}")
            return {
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_servicio"],
                "detalles_usuario": "No se encontró la línea de producto solicitada.",
                "sugerencias": sugerencias,
            }

        # Ordenamiento por fecha y versión
        def parse_updated(val: str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                return datetime.min

        candidates.sort(
            key=lambda item: (
                parse_updated(item["line"].get("updatedAt")),
                item["line"].get("version", 0),
            ),
            reverse=True,
        )

        selected = candidates[0]
        line = selected["line"]
        logger.info(f"Línea seleccionada via {selected['matched_by']}: {line.get('id')}")

        return {
            "id": line.get("id"),
            "name": line.get("name"),
            "title": line.get("title"),
            "parentId": line.get("parentId"),
            "version": line.get("version"),
            "matched_by": selected["matched_by"],
            "principalMin": line.get("principalMin"),
            "principalMax": line.get("principalMax"),
            "timeMin": line.get("timeMin"),
            "timeMax": line.get("timeMax"),
            "timeDefault": line.get("timeDefault"),
            "paymentFrequency": line.get("paymentFrequency"),
        }

    # 3. MANEJO DE ERRORES (Simplificado gracias al cliente)
    except KuentaConnectionError as e:
        logger.error(f"Error de conexión Kuenta: {e}")
        await error_notify(method_name, parent_id_notify_error, str(e))
        return {
            "estado": "error",
            "mensaje": MENSAJES_CLIENTE["error_conexion"],
            "detalles_usuario": "Problemas de conexión con el servicio externo."
        }
    except KuentaAPIError as e:
        logger.error(f"Error API Kuenta: {e}")
        await error_notify(method_name, parent_id_notify_error, f"Status {e.status_code}: {e.response_text}")
        return {
            "estado": "error",
            "mensaje": MENSAJES_CLIENTE["error_servicio"],
            "detalles_usuario": "Error en el servicio externo."
        }
    except Exception as e:
        logger.exception(f"Error no controlado en {method_name}")
        await error_notify(method_name, parent_id_notify_error, f"Error general: {e}")
        return {
            "estado": "error",
            "mensaje": MENSAJES_CLIENTE["error_general"],
            "detalles_usuario": "Ocurrió un error inesperado."
        }

