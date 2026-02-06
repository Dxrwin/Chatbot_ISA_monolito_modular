import json
import logging
import traceback
import re
import httpx
from typing import Optional, Any, Dict


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

    # ===== MÉTODOS QUE FALTABAN Y CAUSABAN EL ERROR =====
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
    # ====================================================

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
            # Reemplazar variables en URL
            final_url = self._replace_variables(self.url)

            # Reemplazar variables en headers
            final_headers = self._process_dict(self.header)

            # Reemplazar variables en body
            final_body = self._process_dict(self.body) if self.body else {}

            logger.info(f"[{self.codigo}] URL final: {final_url}")

            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                for attempt in range(self.reintentos + 1):
                    try:
                        kwargs = {"headers": final_headers}
                        if self.metodo in ["POST", "PUT", "PATCH"]:
                            kwargs["json"] = final_body
                        elif self.metodo == "GET":
                            kwargs["params"] = final_body

                        response = await client.request(self.metodo, final_url, **kwargs)
                        
                        if response.status_code >= 400:
                            await self._log_error(
                                status=response.status_code,
                                error_message=f"Respuesta no exitosa: {response.status_code}",
                                response_text=response.text,
                            )
                        
                        try:
                            data = response.json()
                        except:
                            data = {"raw_text": response.text}

                        return {"status": response.status_code, "data": data}

                    except Exception as e:
                        # Log solo si es el último intento o error crítico
                        if attempt == self.reintentos:
                            await self._log_error(500, str(e), traceback.format_exc())
                            return {"status": 500, "data": {"error": str(e)}}

        except Exception as e:
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