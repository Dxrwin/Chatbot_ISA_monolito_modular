import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def slugify_nombre(value: str) -> str:
    import unicodedata
    if not value: return ""
    normalized = unicodedata.normalize("NFD", value)
    ascii_str = ''.join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    ascii_str = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_str)
    ascii_str = re.sub(r"\s+", " ", ascii_str).strip().lower()
    return ascii_str.replace(" ", "-")

def formatear_fecha_legible(fecha_iso: str) -> str:
    """Convierte ISO 8601 a formato legible español."""
    try:
        dias = {0:"lunes", 1:"martes", 2:"miércoles", 3:"jueves", 4:"viernes", 5:"sábado", 6:"domingo"}
        meses = {1:"enero", 2:"febrero", 3:"marzo", 4:"abril", 5:"mayo", 6:"junio", 7:"julio", 8:"agosto", 9:"septiembre", 10:"octubre", 11:"noviembre", 12:"diciembre"}
        
        fecha_obj = datetime.fromisoformat(str(fecha_iso).replace('Z', '+00:00'))
        return f"{dias[fecha_obj.weekday()]}, {meses[fecha_obj.month]} {fecha_obj.day}, {fecha_obj.year}"
    except Exception:
        return str(fecha_iso)

def formatear_valor_moneda(valor: float) -> str:
    """Formatea float a COP sin decimales."""
    try:
        return f"${round(float(valor)):,}".replace(",", ".")
    except Exception:
        return str(valor)

async def limpiar_valor_principal(raw_principal: str) -> float:
    """Limpia strings sucios (ej: '$2.500.000 COP') a float puro."""
    if not raw_principal: raise ValueError("Valor vacío")
    valor = str(raw_principal).strip().lower()
    
    basura = ['cop', 'pesos', 'valor', 'seria', 'de', 'quiero', 'financiar', 'necesito', 'el', 'millones', 'mil']
    for p in basura: valor = valor.replace(p, '')
    
    valor = re.sub(r'[$ \'"]', '', valor).replace('.', '').replace(',', '')
    numeros = re.findall(r'\d+', valor)
    
    if not numeros: raise ValueError(f"No se pudo extraer número de: {raw_principal}")
    return float(''.join(numeros))