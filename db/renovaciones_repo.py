from typing import Any, Dict


async def insert_renovacion(pool, data: Dict[str, Any]) -> int:
    query = """
        INSERT INTO renovaciones_clientes
        (estado_final_renovacion, estado_pago_payvalida, nombre_cliente)
        VALUES (%s, %s, %s)
    """
    async with pool.acquire() as conn:
        try:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    query,
                    (
                        data["estado_final_renovacion"],
                        data["estado_pago_payvalida"],
                        data["nombre_cliente"],
                    ),
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception:
            await conn.rollback()
            raise


async def exists_renovacion(pool, doc_or_phone: str) -> bool:
    if not doc_or_phone:
        return False
    query = """
        SELECT 1
        FROM renovaciones_clientes
        WHERE nombre_cliente = %s
        LIMIT 1
    """
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, (doc_or_phone,))
            row = await cursor.fetchone()
            return row is not None
