from fastapi import APIRouter, HTTPException
from schemas.admin import ServicioExternoCreateRequest, ConsultaLogsRequest
from db.servicios_repo import crear_servicio_externo
from db.logs_repo import consultar_logs_filtrados

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.post("/servicios-externos", status_code=201)
async def crear_servicio(payload: ServicioExternoCreateRequest):
    try:
        id_new = await crear_servicio_externo(payload.model_dump())
        return {"status": "success", "id": id_new}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logs")
async def consultar_logs(filtros: ConsultaLogsRequest):
    return await consultar_logs_filtrados(filtros.model_dump())