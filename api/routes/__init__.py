from fastapi import APIRouter

from api.routes.health import router as health_router
from api.routes.payable import router as payable_router
from api.routes.products import router as products_router
from api.routes.renovaciones import router as renovaciones_router
from api.routes.webhooks import router as webhooks_router

router = APIRouter()
router.include_router(products_router)
router.include_router(payable_router)
router.include_router(webhooks_router)
router.include_router(renovaciones_router)
router.include_router(health_router)
