"""
Guía de uso del cliente Kuenta
Ejemplos de cómo usar las funciones del cliente en logica.py
"""
from clients.kuenta import (
    kuenta_get_product_lines,
    kuenta_create_payable,
    kuenta_get_payable,
    KuentaAPIError,
    KuentaConnectionError
)
from utils.auth import obtener_token


# ============================================
# Ejemplo 1: GET Product Lines
# ============================================

async def ejemplo_product_lines():
    """
    REEMPLAZO SUGERIDO en webhook_product_lines():
    
    ANTES (líneas 167-190):
    ```python
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        access_token = await obtener_token(client)
        if not access_token:
            # error handling...
        
        headers = {
            "Config-Organization-ID": ORG_ID,  
            "Organization-ID": ORG_ID,
            "Authorization": f"{access_token}"
        }
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.get(API_URL, headers=headers)
                response.raise_for_status()
                data = response.json()
                lines = data.get("data", {}).get("lines", [])
    ```
    
    DESPUÉS:
    ```python
    async with httpx.AsyncClient() as client:
        access_token = await obtener_token(client)
        if not access_token:
            # error handling...
        
        try:
            # Usa el cliente Kuenta - maneja retries automáticamente
            data = await kuenta_get_product_lines(access_token, ORG_ID)
            lines = data.get("data", {}).get("lines", [])
            
            # Tu lógica de negocio aquí (filtering, sorting, matching)
            candidates = []
            for line in lines:
                if line.get("archived"):
                    continue
                # ... resto del filtrado
                    
        except KuentaConnectionError as e:
            await error_notify(method_name, parent_id_notify_error, str(e))
            return {
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_conexion"],
                "detalles_usuario": "No se pudo conectar con el servicio externo."
            }
        except KuentaAPIError as e:
            await error_notify(method_name, parent_id_notify_error, str(e))
            return {
                "estado": "error",
                "mensaje": MENSAJES_CLIENTE["error_servicio"],
                "detalles_usuario": "Error en el servicio externo."
            }
    ```
    """
    pass


# ============================================
# Ejemplo 2: POST Create Payable
# ============================================

async def ejemplo_create_payable():
    """
    REEMPLAZO SUGERIDO en create_payable():
    
    ANTES (líneas 330-430):
    ```python
    async with httpx.AsyncClient() as client:
        token = await obtener_token(client)
        
        new_payload = {
            "creditLineId": payload.creditLineId,
            "principal": principal,
            # ... otros campos
        }
        new_payload = {k: v for k, v in new_payload.items() if v is not None}
        
        headers = {
            "Config-Organization-ID": ORG_ID,
            "Organization-ID": client_id,
            "Authorization": token
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await client.post(PAYABLE_URL, json=new_payload, headers=headers)
                if response.status_code == 201:
                    response_data = response.json()
                    # ...
    ```
    
    DESPUÉS:
    ```python
    async with httpx.AsyncClient() as client:
        token = await obtener_token(client)
        
        # Construir payload (lógica de negocio)
        new_payload = {
            "creditLineId": payload.creditLineId,
            "principal": payload.principal,
            "time": payload.time,
            "disbursementMethod": payload.disbursementMethod,
            "initialFee": payload.initialFee,
            "paymentFrequency": payload.paymentFrequency,
            "source": payload.source,
            "redirectUrl": payload.redirectUrl,
            "callbackUrl": payload.callbackUrl,
            "meta": payload.meta,
        }
        
        try:
            # Usa el cliente - maneja retries y errores automáticamente
            response_data = await kuenta_create_payable(
                access_token=token,
                org_id=ORG_ID,
                client_id=client_id,
                payload=new_payload
            )
            
            # Extraer el ID del crédito (lógica de negocio)
            credit = response_data.get("data", {}).get("credit", {})
            response_credit_id = credit.get("ID")
            
            if not response_credit_id:
                raise HTTPException(
                    status_code=502,
                    detail="No se recibió ID de crédito"
                )
                
            # Continuar con get_payable...
            
        except KuentaConnectionError as e:
            await error_notify(method_name, client_id, str(e))
            return JSONResponse(
                status_code=502,
                content={
                    "estado": "error",
                    "mensaje": MENSAJES_CLIENTE["error_conexion"],
                    "detalles_usuario": "Error de conexión temporal."
                }
            )
        except KuentaAPIError as e:
            await error_notify(method_name, client_id, f"Error API: {e.status_code}")
            return JSONResponse(
                status_code=e.status_code or 500,
                content={
                    "estado": "error",
                    "mensaje": MENSAJES_CLIENTE["error_servicio"],
                    "detalles_usuario": "Error en el servicio externo."
                }
            )
    ```
    """
    pass


# ============================================
# Ejemplo 3: GET Payable (Simulation)
# ============================================

async def ejemplo_get_payable():
    """
    REEMPLAZO SUGERIDO para GET payable (líneas 433-450):
    
    ANTES:
    ```python
    url_prod = f"https://api.kuenta.co/v1/payable/{response_credit_id}"
    logger.info(f"Consultando simulación: {url_prod}")
    
    response_get_simulacion = await client.get(url_prod, headers=headers)
    status_code_simulacion = response_get_simulacion.status_code
    
    if status_code_simulacion == 200 or status_code_simulacion == 201:
        simulacion_data = response_get_simulacion.json()
        credit_data = simulacion_data.get("data", {}).get("credit", {})
    ```
    
    DESPUÉS:
    ```python
    try:
        # Usa el cliente para obtener el payable
        simulacion_data = await kuenta_get_payable(
            access_token=token,
            org_id=ORG_ID,
            client_id=client_id,
            payable_id=response_credit_id
        )
        
        # Extraer datos (lógica de negocio)
        credit_data = simulacion_data.get("data", {}).get("credit", {})
        installments = credit_data.get("installments", [])
        
        if not installments:
            logger.error("No se encontraron installments")
            await error_notify(method_name, client_id, "No cuotas en simulación")
            raise HTTPException(
                status_code=404,
                detail="No se encontraron cuotas en la simulación"
            )
        
        # Continuar con lógica de negocio...
        
    except KuentaNotFoundError as e:
        await error_notify(method_name, client_id, f"Payable no encontrado: {response_credit_id}")
        raise HTTPException(
            status_code=404,
            detail="El payable no fue encontrado"
        )
    except KuentaAPIError as e:
        await error_notify(method_name, client_id, f"Error al consultar payable: {str(e)}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail="Error al consultar la simulación"
        )
    ```
    """
    pass


# ============================================
# Ventajas del nuevo enfoque
# ============================================

"""
✅ VENTAJAS:

1. **Separación de responsabilidades**
   - Cliente: Solo HTTP (requests, headers, timeouts, retries)
   - Lógica: Solo business logic (filtros, validaciones, transformaciones)

2. **Código más limpio**
   - Elimina bloques try/except anidados
   - Reduce código duplicado de retry logic
   - Headers centralizados en el cliente

3. **Mejor manejo de errores**
   - Excepciones específicas por tipo de error
   - Fácil distinguir entre errores de conexión vs. errores de API
   - Contexto rico en las excepciones (status_code, response_text)

4. **Facilita testing**
   - Puedes mockear las funciones del cliente fácilmente
   - No necesitas mockear httpx directamente

5. **Reutilizable**
   - Las funciones del cliente se pueden usar en otros módulos
   - No hay acoplamiento con lógica específica de endpoints
"""
