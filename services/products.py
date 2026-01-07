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
    max_retries = 3
    retry_delay = 5
    timeout = 15

    method_name = "product-lines"
    parent_id_notify_error = f"parent_id para la busqueda de la linea={parent_id}"
    target_slug = slugify_nombre(name) if name else ""

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            access_token = await obtener_token(client)
            if not access_token:
                msg = "No se pudo obtener el token de acceso"
                await error_notify(method_name, parent_id_notify_error, msg)
                return {
                    "estado": "error",
                    "mensaje": MENSAJES_CLIENTE["error_conexion"],
                    "detalles_usuario": "No se pudo obtener el token de acceso. Por favor intenta nuevamente mas tarde.",
                }

            headers = {
                "Config-Organization-ID": ORG_ID,
                "Organization-ID": ORG_ID,
                "Authorization": f"{access_token}",
            }

            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.get(API_URL, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    logger.info(f"Respuesta recibida de API para buscar la linea: {data}")
                    lines = data.get("data", {}).get("lines", [])

                    candidates = []
                    for line in lines:
                        if line.get("archived"):
                            continue
                        if entity_id and line.get("entityID") != entity_id:
                            continue
                        if product_type is not None and line.get("productType") != product_type:
                            continue
                        if tipo is not None and line.get("type") != tipo:
                            continue

                        parent_match = line.get("parentId") == parent_id
                        slug_name = slugify_nombre(line.get("name", ""))
                        slug_title = slugify_nombre(line.get("title", ""))
                        slug_match = bool(target_slug) and (slug_name == target_slug or slug_title == target_slug)

                        if not (parent_match or slug_match):
                            continue

                        candidates.append(
                            {
                                "line": line,
                                "matched_by": "parentId" if parent_match else "slug",
                            }
                        )

                    if not candidates and target_slug:
                        for line in lines:
                            if line.get("archived"):
                                continue
                            if entity_id and line.get("entityID") != entity_id:
                                continue
                            slug_name = slugify_nombre(line.get("name", ""))
                            slug_title = slugify_nombre(line.get("title", ""))
                            if target_slug in slug_name or target_slug in slug_title:
                                candidates.append({"line": line, "matched_by": "partial-slug"})

                    if not candidates:
                        msg = f"No se encontro la linea con parentId {parent_id} ni slug {target_slug}"
                        await error_notify(method_name, parent_id_notify_error, msg)
                        sugerencias = [slugify_nombre(l.get("name", "")) for l in lines][:10]
                        return {
                            "estado": "error",
                            "mensaje": MENSAJES_CLIENTE["error_servicio"],
                            "detalles_usuario": "No se encontro la linea de producto solicitada. Verifica el nombre o intenta mas tarde.",
                            "sugerencias": sugerencias,
                        }

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

                    logger.info(f"Linea encontrada via {selected['matched_by']}: {line}")
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

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                    logger.warning(f"Intento {attempt}/{max_retries} fallido por timeout o conexion: {e}")
                    if attempt == max_retries:
                        return {
                            "estado": "error",
                            "mensaje": MENSAJES_CLIENTE["error_conexion"],
                            "detalles_usuario": "No se pudo conectar con el servicio externo. Por favor intenta nuevamente mas tarde.",
                        }
                    await asyncio.sleep(retry_delay * attempt)

                except httpx.HTTPStatusError as e:
                    logger.error(f"Error HTTP {e.response.status_code} en API externa: {e.response.text}")
                    await error_notify(
                        method_name, parent_id_notify_error, f"Error en API externa: {e.response.text}"
                    )
                    if 500 <= e.response.status_code < 600 and attempt < max_retries:
                        await asyncio.sleep(retry_delay * attempt)
                        continue
                    return {
                        "estado": "error",
                        "mensaje": MENSAJES_CLIENTE["error_servicio"],
                        "detalles_usuario": "El servicio externo no esta disponible. Por favor intenta mas tarde.",
                    }

            msg = "Error persistente al consultar API externa"
            await error_notify(method_name, parent_id_notify_error, msg)
            return {
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_conexion"],
                "detalles_usuario": "No se pudo obtener respuesta del servicio externo. Por favor intenta mas tarde.",
            }

    except Exception as e:
        logger.error(f"Error general en obtener_product_line: {e}")
        await error_notify(method_name, parent_id_notify_error, f"Error general: {e}")
        return {
            "estado": "error",
            "mensaje": MENSAJES_CLIENTE["error_general"],
            "detalles_usuario": "Ocurrio un error inesperado. Por favor intenta nuevamente mas tarde.",
        }
