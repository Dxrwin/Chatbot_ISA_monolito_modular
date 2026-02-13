from typing import Optional
import logging
from fastapi import APIRouter
from services.products import obtener_product_line

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/product-lines/{parent_id}")
async def product_lines(
    parent_id: str,
    name: Optional[str] = None,
    entity_id: Optional[str] = None,
    product_type: Optional[int] = None,
    tipo: Optional[int] = None,
):
    logger.info(f"[PRODUCTS_ROUTE] Solicitud de líneas de producto para parent_id: {parent_id}")
    return await obtener_product_line(
        parent_id,
        name=name,
        entity_id=entity_id,
        product_type=product_type,
        tipo=tipo,
    )
