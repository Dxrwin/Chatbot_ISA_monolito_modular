import json
import logging
import traceback
import re
import asyncio
from fastapi.responses import JSONResponse
import httpx
from typing import Optional, Any, Dict
from utils.notify_error import info_notify
from db.logs_repo import insertar_log
from db.servicios_repo import obtener_servicio_externo_por_codigo

logger = logging.getLogger(__name__)

class ExternalClient:
    """
    Cliente para ejecutar peticiones HTTP a servicios externos configurados en BD.
    Soporta reemplazo dinámico de variables en URL, headers y body.
    """

    # Patrón compilado para placeholders {variable}
    VAR_PATTERN = re.compile(r'\{([^}]+)\}')

    def __init__(
        self,
        nombre_servicio: str,
        codigo: str,
        url: str,
        metodo: str,
        timeout_ms: int = 10000,
        reintentos: int = 0,
        header: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ):
        self.nombre_servicio = nombre_servicio
        self.codigo = codigo
        self.url = url
        self.metodo = metodo.upper()
        self.timeout_ms = timeout_ms
        self.timeout_s = timeout_ms / 1000
        self.reintentos = reintentos
        self.header = header or {}
        self.body = body or {}
        self.dynamic_values = {}  # Variables dinámicas a reemplazar
        self.client_id = None  # Para logging

    @classmethod
    async def from_code(cls, codigo: str, client_id: Optional[str] = None) -> "ExternalClient":
        """
        Carga un servicio externo desde la BD usando su código.
        """
        servicio = await obtener_servicio_externo_por_codigo(codigo)
        if not servicio:
            raise ValueError(f"Servicio externo '{codigo}' no encontrado en BD")

        # Crear instancia con datos de BD
        instance = cls(
            nombre_servicio=servicio.get("nombre_servicio"),
            codigo=servicio.get("codigo"),
            url=servicio.get("url"),
            metodo=servicio.get("metodo"),
            timeout_ms=servicio.get("timeout_ms", 10000),
            reintentos=servicio.get("reintentos", 0),
            header=servicio.get("header", {}),
            body=servicio.get("body", {}),
        )
        instance.client_id = client_id
        return instance

    
    def set_url(self, url: str) -> None:
        """Establece la URL (puede contener placeholders)"""
        self.url = url

    def set_path(self, path: str) -> None:
        """Agrega un path a la URL existente"""
        self.url = self.url.rstrip("/") + path

    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        Establece headers adicionales.
        Se mergean con los headers de BD.
        """
        self.header.update(headers or {})

    def set_body(self, body: Dict[str, Any]) -> None:
        """Establece el body (puede contener placeholders)"""
        self.body = body or {}

    def set_dynamic_values(self, values: Dict[str, Any]) -> None:
        """Establece variables dinámicas para reemplazos."""
        self.dynamic_values.update(values or {})

    def _replace_variables(self, text: str) -> str:
        """Reemplaza placeholders en texto."""
        if not isinstance(text, str):
            return text

        def replacer(match):
            var_name = match.group(1)
            if var_name in self.dynamic_values:
                return str(self.dynamic_values[var_name])
            return match.group(0)

        return self.VAR_PATTERN.sub(replacer, text)

    def _process_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa recursivamente un diccionario reemplazando variables."""
        if not isinstance(d, dict):
            return d

        result = {}
        for key, value in d.items():
            # Si el valor es string, intentar reemplazar variables
            if isinstance(value, str):
                result[key] = self._replace_variables(value)
            # Si es dict, recursividad
            elif isinstance(value, dict):
                result[key] = self._process_dict(value)
            # Si es lista, iterar
            elif isinstance(value, list):
                result[key] = [self._process_dict(i) if isinstance(i, dict) else i for i in value]
            else:
                result[key] = value
        return result

    async def run(self) -> Dict[str, Any]:
        """Ejecuta la petición HTTP al servicio externo."""
        try:
            # ========== PASO 1: REEMPLAZO DE VARIABLES DINÁMICAS ==========
            # Reemplaza placeholders {variable} en URL, headers y body con valores reales
            # Ejemplo: "{access_token}" se convierte en "Bearer eyJ..."
            final_url = self._replace_variables(self.url)
            final_headers = self._process_dict(self.header)
            final_body = self._process_dict(self.body) if self.body else {}

            # ========== LOGS DETALLADOS ANTES DE LA PETICIÓN ==========
            logger.info(f"\n{'='*80}")
            logger.info(f"[{self.codigo}] INICIANDO PETICIÓN HTTP")
            logger.info(f"{'='*80}")
            logger.info(f"URL:     {final_url} \n")
            logger.info(f"Método:  {self.metodo} \n")
            logger.info(f"Reintentos: {self.reintentos} \n")
            logger.info(f"Headers: {json.dumps(final_headers, indent=2, ensure_ascii=False)}\n")
            logger.info(f"Body:    {json.dumps(final_body, indent=2, ensure_ascii=False) if final_body else 'No body'} \n")
            logger.info(f"{'='*80}\n")

            try:
                from utils.notify_error import info_notify
                await info_notify(
                    method_name=f"external_client:{self.codigo}",
                    client_id=self.client_id or "N/A",
                    info_message=f"Ejecutando {self.metodo} a '{self.nombre_servicio}' | URL: {final_url}"
                )
            except Exception as notify_err:
                logger.debug(f"No se pudo enviar notificación previa: {notify_err}")

            # ========== PASO 2: EJECUCIÓN DE LA PETICIÓN HTTP ==========
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                # Sistema de reintentos configurable desde BD
                for attempt in range(self.reintentos + 1):
                    try:
                        # --- Gestión de Métodos HTTP ---
                        # Preparamos los argumentos según el tipo de método HTTP
                        kwargs = {"headers": final_headers}

                        logger.info(f"[{self.codigo}] Método: {self.metodo}")
                        logger.info(f"[{self.codigo}] Headers: {final_headers}")
                        
                        
                        # POST, PUT, PATCH: Envían datos en el BODY como JSON
                        # - Se usa 'json' para que httpx serialice automáticamente
                        # - Content-Type: application/json se agrega automáticamente
                        if self.metodo in ["POST", "PUT", "PATCH"]:
                            kwargs["json"] = final_body
                            logger.debug(f"[{self.codigo}] Método {self.metodo}: enviando data en BODY como JSON")
                        
                        # GET: Envía parámetros en la QUERY STRING (URL)
                        # - Se usa 'params' para construir ?param1=value1&param2=value2
                        # - No se envía body
                        elif self.metodo == "GET":
                            kwargs["params"] = final_body
                            logger.debug(f"[{self.codigo}] Método GET: enviando data como QUERY PARAMS")
                        
                        # DELETE: Puede o no llevar body según la API
                        # - Algunos servicios esperan body, otros no
                        # - Por defecto lo enviamos como JSON si existe
                        elif self.metodo == "DELETE":
                            if final_body:
                                kwargs["json"] = final_body
                                logger.debug(f"[{self.codigo}] Método DELETE: enviando data en BODY")
                        
                        # Ejecutar la petición HTTP usando el método genérico request()
                        # Esto es equivalente a hacer: client.get(), client.post(), etc.
                        response = await client.request(self.metodo, final_url, **kwargs)

                        # ========== PASO 3: PROCESAMIENTO DE LA RESPUESTA ==========
                        # Intentar parsear como JSON (la mayoría de APIs REST retornan JSON)
                        try:
                            data = response.json()
                            response_data = data.get("data",{})
                            #estatus de la respuesta
                            status = data.get("status",{})
                            logger.info(f"[{self.codigo}] Status: {status}" + "\n")

                            
                        except:
                            # Si no es JSON válido, guardar como texto plano
                            data = {"raw_text": response.text}
                            response_data = data.get("data",{})
                            #logger.info(f"[{self.codigo}] Respuesta: {response_data}")

                        # ========== LOGS DETALLADOS DESPUÉS DE LA RESPUESTA ==========
                        logger.info(f"[{self.codigo}] RESPUESTA RECIBIDA")
                        # response_data = data.get("data",{})
                        # logger.info(f"\n{'='*80}")
                        # logger.info(f"response_data: {response_data}")


                        # ========== PASO 4: NOTIFICACIONES Y LOGS EN BD ==========
                        if response.status_code == 200 or response.status_code == 201:
                            # Respuesta exitosa (2xx, 3xx)
                            try:
                                await info_notify(
                                    method_name=f"external_client:{self.codigo}",
                                    client_id=self.client_id or "N/A",
                                    info_message=f"|Respuesta exitosa de '{self.nombre_servicio}' | Status: {response.status_code}"
                                )
                                # Retornar resultado exitoso
                                return {"status": response.status_code, "data": response_data}
                            except Exception as notify_err:
                                logger.debug(f"No se pudo enviar notificación de éxito: {notify_err}")
                        else:
                            # Respuesta con error (4xx, 5xx)
                            logger.error(f"[{self.codigo}] Error HTTP {response.status_code}: {response.text}")
                            await self._log_error(
                                status=response.status_code,
                                error_message=f"Respuesta no exitosa: {response.status_code}",
                                response_text=response.text,
                            )


                    except httpx.TimeoutException as timeout_err:
                        # Error de timeout específico
                        logger.error(f"[{self.codigo}]  TIMEOUT en intento {attempt + 1}/{self.reintentos + 1}: {timeout_err}")
                        if attempt == self.reintentos:
                            await self._log_error(504, "Gateway Timeout", str(timeout_err))

                            return JSONResponse(status_code=504, content={"status": 504, "data": {"error": "Timeout al conectar con el servicio externo"}})
                        
                        if attempt < self.reintentos:
                            logger.warning(f"[{self.codigo}] Reintentando en 1 segundo...")
                            await asyncio.sleep(1)
                    
                    except httpx.RequestError as req_err:
                        # Errores de conexión, DNS, etc.
                        logger.error(f"[{self.codigo}] 🔌 ERROR DE CONEXIÓN en intento {attempt + 1}/{self.reintentos + 1}: {req_err}")
                        if attempt == self.reintentos:
                            await self._log_error(503, "Service Unavailable", str(req_err))
                            return {"status": 503, "data": {"error": "No se pudo conectar con el servicio externo"}}
                        
                        if attempt < self.reintentos:
                            logger.warning(f"[{self.codigo}] Reintentando en 1 segundo...")
                            await asyncio.sleep(1)
                    
                    except Exception as e:
                        # Cualquier otro error inesperado
                        logger.error(f"[{self.codigo}]  ERROR INESPERADO en intento {attempt + 1}/{self.reintentos + 1}: {str(e)}")
                        if attempt == self.reintentos:
                            await self._log_error(500, str(e), traceback.format_exc())
                            return {"status": 500, "data": {"error": str(e)}}
                        
                        if attempt < self.reintentos:
                            logger.warning(f"[{self.codigo}] Reintentando en 1 segundo...")
                            await asyncio.sleep(1)

        except Exception as e:
            # Error crítico fuera del loop de reintentos
            logger.error(f"\n{'='*80}")
            logger.error(f"[{self.codigo}] ERROR CRÍTICO")
            logger.error(f"{'='*80}")
            logger.error(f"Mensaje: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.error(f"{'='*80}\n")
            await self._log_error(500, str(e), traceback.format_exc())
            return {"status": 500, "data": {"error": f"Error interno: {str(e)}"}}

    async def _log_error(self, status: int, error_message: str, response_text: str):
        """Registra errores en la BD usando el repo modular."""
        try:
            await insertar_log(
                method_name=f"external_client:{self.codigo}",
                client_id=self.client_id or "N/A",
                error_message=error_message,
                http_code=status,
                tipo="error",
                nombre_archivo="utils/external_client.py",
                traceback_str=traceback.format_exc(),
                respuesta_api=response_text,
                payload_enviado=json.dumps(self.body) if self.body else None,
            )
        except Exception:
            logger.error("Failed to persist log for external_client", exc_info=True)