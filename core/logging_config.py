import logging
import sys

def setup_logging():
    """
    Configura el logging de toda la aplicación.
    Debe ser llamado una sola vez en el punto de entrada (main.py).
    """
    # Definir el formato que solicitaste
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    
    # Configuración básica
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # StreamHandler envía los logs a la consola estándar (stdout)
            # Esto es crucial para ver los logs en Docker o terminales de servidores
            logging.StreamHandler(sys.stdout)
        ],
        # force=True es vital: sobrescribe la config por defecto de Uvicorn/FastAPI
        force=True
    )
    
    # Opcional: Reducir ruido de librerías externas si es necesario
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Crear un logger de prueba para confirmar que inició
    logger = logging.getLogger(__name__)
    logger.info("✅ Sistema de Logging inicializado correctamente")