"""
Script de prueba manual para validar PayableRequest
Ejecutar: python test_payable_validation.py
"""
from schemas.payable import PayableRequest
from pydantic import ValidationError


def test_valid_payable():
    """Prueba con datos válidos"""
    print("\n" + "="*60)
    print("TEST 1: Datos válidos (tipos correctos)")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": 2500000.0,
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000.0,
        "disbursementMethod": "bank_transfer",
        "source": "web",
        "redirectUrl": "https://example.com/success",
        "callbackUrl": "https://example.com/callback",
        "meta": {"userId": "12345", "campaign": "renovacion"}
    }
    
    try:
        payable = PayableRequest(**data)
        print("✅ ÉXITO: Validación correcta")
        print(f"   creditLineId: {payable.creditLineId}")
        print(f"   principal: ${payable.principal:,.0f}")
        print(f"   time: {payable.time} meses")
        print(f"   initialFee: ${payable.initialFee:,.0f}")
    except ValidationError as e:
        print(f"❌ ERROR: {e}")


def test_string_conversion():
    """Prueba conversión de strings a números"""
    print("\n" + "="*60)
    print("TEST 2: Conversión de strings a números")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": "2500000",  # String que debe convertirse a float
        "time": "6",              # String que debe convertirse a int
        "paymentFrequency": "30", # String que debe convertirse a int
        "initialFee": "500000"    # String que debe convertirse a float
    }
    
    try:
        payable = PayableRequest(**data)
        print("✅ ÉXITO: Conversión de strings correcta")
        print(f"   principal: {payable.principal} (tipo: {type(payable.principal).__name__})")
        print(f"   time: {payable.time} (tipo: {type(payable.time).__name__})")
        print(f"   initialFee: {payable.initialFee} (tipo: {type(payable.initialFee).__name__})")
    except ValidationError as e:
        print(f"❌ ERROR: {e}")


def test_comma_decimal():
    """Prueba conversión de números con coma decimal"""
    print("\n" + "="*60)
    print("TEST 3: Conversión de números con coma como decimal")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": "2500000,50",  # Coma como separador decimal
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": "500000,75"   # Coma como separador decimal
    }
    
    try:
        payable = PayableRequest(**data)
        print("✅ ÉXITO: Conversión con coma decimal correcta")
        print(f"   principal: {payable.principal}")
        print(f"   initialFee: {payable.initialFee}")
    except ValidationError as e:
        print(f"❌ ERROR: {e}")


def test_empty_creditLineId():
    """Prueba creditLineId vacío (debe fallar)"""
    print("\n" + "="*60)
    print("TEST 4: creditLineId vacío (debe fallar)")
    print("="*60)
    
    data = {
        "creditLineId": "",  # Vacío, debe generar error
        "principal": 2500000,
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000
    }
    
    try:
        payable = PayableRequest(**data)
        print("❌ FALLO: Debería haber rechazado creditLineId vacío")
    except ValidationError as e:
        print("✅ ÉXITO: Validación rechazó correctamente el creditLineId vacío")
        print(f"   Error: {e.errors()[0]['msg']}")


def test_empty_principal():
    """Prueba principal vacío (debe fallar)"""
    print("\n" + "="*60)
    print("TEST 5: principal vacío (debe fallar)")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": "",  # Vacío, debe generar error
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000
    }
    
    try:
        payable = PayableRequest(**data)
        print("❌ FALLO: Debería haber rechazado principal vacío")
    except ValidationError as e:
        print("✅ ÉXITO: Validación rechazó correctamente el principal vacío")
        print(f"   Error: {e.errors()[0]['msg']}")


def test_invalid_number():
    """Prueba número inválido (debe fallar)"""
    print("\n" + "="*60)
    print("TEST 6: Número inválido (debe fallar)")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": "abc123",  # String no convertible, debe generar error
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000
    }
    
    try:
        payable = PayableRequest(**data)
        print("❌ FALLO: Debería haber rechazado número inválido")
    except ValidationError as e:
        print("✅ ÉXITO: Validación rechazó correctamente el número inválido")
        print(f"   Error: {e.errors()[0]['msg']}")


def test_empty_disbursement():
    """Prueba disbursementMethod vacío (debe convertir a None)"""
    print("\n" + "="*60)
    print("TEST 7: disbursementMethod vacío (debe convertir a None)")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": 2500000,
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000,
        "disbursementMethod": ""  # Vacío, debe convertirse a None
    }
    
    try:
        payable = PayableRequest(**data)
        print("✅ ÉXITO: Convirtió string vacío a None correctamente")
        print(f"   disbursementMethod: {payable.disbursementMethod} (tipo: {type(payable.disbursementMethod).__name__})")
    except ValidationError as e:
        print(f"❌ ERROR: {e}")


def test_optional_fields():
    """Prueba campos opcionales omitidos"""
    print("\n" + "="*60)
    print("TEST 8: Campos opcionales omitidos")
    print("="*60)
    
    data = {
        "creditLineId": "CL123456",
        "principal": 2500000,
        "time": 6,
        "paymentFrequency": 30,
        "initialFee": 500000
        # Campos opcionales no incluidos
    }
    
    try:
        payable = PayableRequest(**data)
        print("✅ ÉXITO: Validación con campos opcionales omitidos")
        print(f"   disbursementMethod: {payable.disbursementMethod}")
        print(f"   source: {payable.source}")
        print(f"   redirectUrl: {payable.redirectUrl}")
        print(f"   callbackUrl: {payable.callbackUrl}")
        print(f"   meta: {payable.meta}")
    except ValidationError as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("PRUEBAS DE VALIDACIÓN DE PAYABLE REQUEST")
    print("="*60)
    
    test_valid_payable()
    test_string_conversion()
    test_comma_decimal()
    test_empty_creditLineId()
    test_empty_principal()
    test_invalid_number()
    test_empty_disbursement()
    test_optional_fields()
    
    print("\n" + "="*60)
    print("PRUEBAS COMPLETADAS")
    print("="*60 + "\n")
