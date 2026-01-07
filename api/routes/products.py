from typing import Optional

from fastapi import APIRouter

from services.products import obtener_product_line

router = APIRouter()


@router.get("/product-lines/{parent_id}")
async def product_lines(
    parent_id: str,
    name: Optional[str] = None,
    entity_id: Optional[str] = None,
    product_type: Optional[int] = None,
    tipo: Optional[int] = None,
):
    return await obtener_product_line(
        parent_id,
        name=name,
        entity_id=entity_id,
        product_type=product_type,
        tipo=tipo,
    )
