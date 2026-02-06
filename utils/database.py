import aiomysql
import logging
from utils.config import settings

db_config = {
    "host": settings.DB_HOST,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD_RENOVACION,
    "database": settings.DB_NAME_RENOVACION
}


logger = logging.getLogger(__name__)



async def insertar_flujo_correo_post_agente(
    nombre_cliente: str,
    correo_enviado: str,
    numero_telefono: str,
    linea_universitaria: str,
) -> int:
    """
    Inserta (o actualiza) un registro en flujo_correo_post_agente.

    - numero_telefono es único, si ya existe se actualiza el registro
    y se refresca fecha_envio.
    """
    method_name = "insertar_flujo_correo_post_agente"

    try:
        connection = await aiomysql.connect(
            host= db_config["host"],
            user= db_config["user"],
            password= db_config["password"],
            db= db_config["database"]
        )

        try:
            async with connection.cursor() as cursor:
                query = """
                    INSERT INTO flujo_correo_post_agente (
                        nombre_cliente,
                        correo_enviado,
                        numero_telefono,
                        linea_universitaria
                    )
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nombre_cliente = VALUES(nombre_cliente),
                        correo_enviado = VALUES(correo_enviado),
                        linea_universitaria = VALUES(linea_universitaria),
                        fecha_envio = CURRENT_TIMESTAMP;
                """

                await cursor.execute(
                    query,
                    (
                        nombre_cliente,
                        correo_enviado,
                        numero_telefono,
                        linea_universitaria,
                    ),
                )

                await connection.commit()

                insert_id = cursor.lastrowid
                logger.info(
                    f"[{method_name}] Registro insertado/actualizado. ID: {insert_id} | Teléfono: {numero_telefono}"
                )

                # Si fue UPDATE, lastrowid puede venir 0; a nivel de negocio
                # igual ya quedó registrado.
                return insert_id or 0

        finally:
            connection.close()

    except aiomysql.Error as db_error:
        logger.error(f"[{method_name}] Error de base de datos: {str(db_error)}", exc_info=True)
        # Aquí puedes llamar a error_notify si quieres
        # await error_notify(...)
        raise


async def insertar_renovacion_vinculada(renovacion_data: dict) -> tuple[str, int]:
    """
    Inserta una renovación de crédito con relación padre-hijo de forma transaccional.
    
    Flujo:
    1. Mapea el estado numérico (int) a su representación textual
    2. Inserta en tabla 'credito' (padre) con ID_Credito_simulacion como PK
    3. Inserta en tabla 'renovaciones_clientes' (hija) usando el ID como FK
    4. Ejecuta commit si ambas inserciones son exitosas
    5. Ejecuta rollback automático si cualquier paso falla
    
    Args:
        renovacion_data: Diccionario con las claves:
            - ID_Credito_simulacion (str): PK del crédito
            - numero_telefono (str): Teléfono del cliente
            - correo_cliente (str): Email del cliente
            - nombre_cliente (str): Nombre del cliente
            - credito_data (dict): Datos financieros del crédito con:
                - referencia_simulacion (str, opcional)
                - nombre_linea_simulacion (str, opcional)
                - cuota_inicial_simulacion (float, opcional)
                - semestre_renovacion (str, opcional)
                - estado_credito_post_confirmado (int): Estado numérico 0-20
                - valor_solicitud_express (float, opcional)
    
    Returns:
        Tupla (ID_Credito_simulacion: str, id_renovacion_cliente: int)
    
    Raises:
        ValueError: Si el estado_credito_post_confirmado no está en el rango válido
        aiomysql.Error: Si ocurre un error de base de datos
    """
    method_name = "insertar_renovacion_vinculada"
    
    # Diccionario de mapeo de estados numéricos a textuales
    ESTADOS_CREDITO = {
        0: "EN PROCESO",
        1: "PENDIENTE",
        2: "APROBADO",
        3: "RECHAZADO",
        4: "FALLIDO",
        5: "FORMALIZADO",
        6: "DESEMBOLSANDO",
        7: "DESEMBOLSADO",
        8: "PAGADO",
        9: "DESISTIDO",
        10: "MORA",
        11: "NO RECLAMADO",
        12: "SIMULACION",
        13: "INCOMPLETO",
        14: "VERIFICACION",
        15: "CASTIGADO",
        16: "PAGO PENDIENTE",
        17: "ESPERANDO GARANTIAS",
        18: "REFINANCIANDO",
        19: "REFINANCIADO",
        20: "CONTRA PROPUESTA",
    }
    
    # Extraer datos del request
    id_credito = renovacion_data["ID_Credito_simulacion"]
    numero_telefono = renovacion_data["numero_telefono"]
    correo_cliente = renovacion_data["correo_cliente"]
    nombre_cliente = renovacion_data["nombre_cliente"]
    credito_data = renovacion_data["credito_data"]
    
    # Validar y mapear el estado
    estado_num = credito_data["estado_credito_post_confirmado"]
    if estado_num not in ESTADOS_CREDITO:
        raise ValueError(
            f"Estado de crédito inválido: {estado_num}. Debe estar entre 0 y 20."
        )
    
    estado_texto = ESTADOS_CREDITO[estado_num]
    
    logger.info(
        f"[{method_name}] Iniciando inserción transaccional | "
        f"ID_Credito: {id_credito} | Cliente: {nombre_cliente} | Estado: {estado_num} ({estado_texto})"
    )
    
    connection = None
    try:
        # Establecer conexión
        connection = await aiomysql.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            db=db_config["database"],
            autocommit=False  # Importante: desactivar autocommit para transacciones manuales
        )
        
        async with connection.cursor() as cursor:
            try:
                # Iniciar transacción explícita
                await connection.begin()
                
                # ========================================
                # PASO 1: Insertar en tabla CREDITO (Padre)
                # ========================================
                query_credito = """
                    INSERT INTO credito (
                        ID_Credito_simulacion,
                        referencia_simulacion,
                        nombre_linea_simulacion,
                        cuota_inicial_simulacion,
                        semestre_renovacion,
                        estado_credito_post_confirmado,
                        estado_credito,
                        valor_solicitud_express
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                await cursor.execute(
                    query_credito,
                    (
                        id_credito,
                        credito_data.get("referencia_simulacion"),
                        credito_data.get("nombre_linea_simulacion"),
                        credito_data.get("cuota_inicial_simulacion"),
                        credito_data.get("semestre_renovacion"),
                        estado_num,  # INT
                        estado_texto,  # VARCHAR mapeado
                        credito_data.get("valor_solicitud_express"),
                    ),
                )
                
                logger.info(
                    f"[{method_name}] ✓ Registro insertado en tabla CREDITO | ID: {id_credito}"
                )
                
                # ========================================
                # PASO 2: Insertar en tabla RENOVACIONES_CLIENTES (Hija)
                # ========================================
                query_renovacion = """
                    INSERT INTO renovaciones_clientes (
                        numero_telefono,
                        correo_cliente,
                        nombre_cliente,
                        id_credito_simulacion
                    ) VALUES (%s, %s, %s, %s)
                """
                
                await cursor.execute(
                    query_renovacion,
                    (
                        numero_telefono,
                        correo_cliente,
                        nombre_cliente,
                        id_credito,  # FK que referencia a credito.ID_Credito_simulacion
                    ),
                )
                
                id_renovacion = cursor.lastrowid
                
                logger.info(
                    f"[{method_name}] ✓ Registro insertado en tabla RENOVACIONES_CLIENTES | "
                    f"ID: {id_renovacion} | FK: {id_credito}"
                )
                
                # ========================================
                # PASO 3: COMMIT - Confirmar transacción
                # ========================================
                await connection.commit()
                
                logger.info(
                    f"[{method_name}] ✓ TRANSACCIÓN COMPLETADA EXITOSAMENTE | "
                    f"Crédito: {id_credito} | Renovación: {id_renovacion}"
                )
                
                return (id_credito, id_renovacion)
                
            except Exception as e:
                # ========================================
                # ROLLBACK - Revertir cambios en caso de error
                # ========================================
                await connection.rollback()
                logger.error(
                    f"[{method_name}] ✗ ROLLBACK ejecutado | Error: {str(e)}",
                    exc_info=True
                )
                raise
    
    except aiomysql.Error as db_error:
        logger.error(
            f"[{method_name}] Error de base de datos: {str(db_error)}",
            exc_info=True
        )
        raise
    
    finally:
        if connection:
            connection.close()
            logger.debug(f"[{method_name}] Conexión a base de datos cerrada")

