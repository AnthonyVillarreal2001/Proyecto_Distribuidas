"""
Script para crear datos de prueba (seed data)
"""
import sys
from pathlib import Path
import asyncio
import httpx

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.config import get_settings
from shared.enums import UserRole, TipoEntrega

settings = get_settings()

# URL base del API Gateway
BASE_URL = f"http://localhost:{settings.api_gateway_port}"


async def create_test_users():
    """Crea usuarios de prueba"""
    print("\n👤 Creando usuarios de prueba...")

    users = [{
        "email": "admin@logiflow.com",
        "username": "admin",
        "password": "admin123",
        "full_name": "Administrador Sistema",
        "role": "ADMIN",
        "phone": "0999999999"
    }, {
        "email": "gerente@logiflow.com",
        "username": "gerente",
        "password": "gerente123",
        "full_name": "Juan Pérez - Gerente",
        "role": "GERENTE",
        "phone": "0998888888"
    }, {
        "email": "supervisor@logiflow.com",
        "username": "supervisor",
        "password": "supervisor123",
        "full_name": "María García - Supervisor",
        "role": "SUPERVISOR",
        "phone": "0997777777",
        "zone_id": "QUITO_NORTE"
    }, {
        "email": "repartidor1@logiflow.com",
        "username": "repartidor1",
        "password": "repartidor123",
        "full_name": "Carlos Rodríguez - Repartidor",
        "role": "REPARTIDOR",
        "phone": "0996666666",
        "zone_id": "QUITO_NORTE",
        "fleet_type": "MOTORIZADO"
    }, {
        "email": "cliente1@gmail.com",
        "username": "cliente1",
        "password": "cliente123",
        "full_name": "Ana López - Cliente",
        "role": "CLIENTE",
        "phone": "0995555555"
    }]

    created_users = []

    async with httpx.AsyncClient() as client:
        for user_data in users:
            try:
                response = await client.post(f"{BASE_URL}/api/auth/register",
                                             json=user_data,
                                             timeout=10.0)

                if response.status_code == 201:
                    result = response.json()
                    print(
                        f"  ✓ Usuario creado: {user_data['username']} ({user_data['role']})"
                    )
                    created_users.append(result)
                else:
                    print(
                        f"  ✗ Error creando {user_data['username']}: {response.text}"
                    )

            except Exception as e:
                print(f"  ✗ Error creando {user_data['username']}: {e}")

    return created_users


async def create_test_data():
    """Crea datos de prueba completos"""
    print("=" * 60)
    print("LogiFlow - Creación de Datos de Prueba")
    print("=" * 60)

    # Crear usuarios
    users = await create_test_users()

    if not users:
        print("\n❌ No se pudieron crear usuarios. Abortando...")
        return

    print("\n" + "=" * 60)
    print("✅ Datos de prueba creados exitosamente")
    print("=" * 60)
    print("\n📝 Usuarios de prueba:")
    print("  - admin / admin123 (ADMIN)")
    print("  - gerente / gerente123 (GERENTE)")
    print("  - supervisor / supervisor123 (SUPERVISOR)")
    print("  - repartidor1 / repartidor123 (REPARTIDOR)")
    print("  - cliente1 / cliente123 (CLIENTE)")
    print("\n💡 Usa estos usuarios para probar el sistema")


async def main():
    """Función principal"""
    try:
        await create_test_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
