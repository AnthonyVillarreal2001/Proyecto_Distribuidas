"""
Tests de endpoints del sistema usando pytest y pytest-asyncio
"""
import pytest
import pytest_asyncio
import httpx

BASE_URL = "http://localhost:5000"  # API Gateway


@pytest.mark.asyncio
async def test_health_check():
    """Prueba health check"""
    print("\n🏥 Probando health check...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=10.0)
            assert response.status_code == 200, f"Health check falló: {response.status_code}"
            data = response.json()
            print(f"  ✓ Sistema: {data.get('overall_status', 'unknown')}")

            for service_name, service_data in data.get('services', {}).items():
                status = service_data.get('status', 'unknown')
                print(f"  ✓ {service_name}: {status}")

        except httpx.ConnectError:
            pytest.skip("Servidor no está corriendo en localhost:5000. Inicia el backend primero.")
        except Exception as e:
            pytest.fail(f"Error inesperado en health check: {e}")


@pytest_asyncio.fixture
async def access_token():
    """Fixture async que hace login y devuelve el token"""
    print("\n🔐 Probando flujo de autenticación (login)...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/auth/login",
                json={
                    "username": "cliente1",
                    "password": "cliente123"
                },
                timeout=10.0
            )

            assert response.status_code == 200, f"Login falló: {response.text}"
            data = response.json()
            token = data['access_token']
            print(f"  ✓ Login exitoso - Token obtenido")
            print(f"  ✓ Usuario: {data['user']['username']} ({data['user']['role']})")

            return token

        except httpx.ConnectError:
            pytest.skip("No se pudo conectar al servidor. Asegúrate de que el backend esté corriendo.")
        except Exception as e:
            pytest.fail(f"Error en login: {e}")


@pytest.mark.asyncio
async def test_pedido_flow(access_token: str):
    """Prueba flujo de pedidos"""
    print("\n📦 Probando flujo de pedidos...")

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        print("  → Creando pedido...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/pedidos",
                json={
                    "cliente_id": 5,
                    "origen_direccion": "Av. Amazonas N123, Quito",
                    "destino_direccion": "Av. 6 de Diciembre N456, Quito",
                    "tipo_entrega": "URBANA_RAPIDA",
                    "descripcion": "Paquete de documentos",
                    "peso_kg": 2.5,
                    "contacto_nombre": "Pedro Gómez",
                    "contacto_telefono": "0991234567"
                },
                headers=headers,
                timeout=10.0
            )

            assert response.status_code == 201, f"Error creando pedido: {response.text}"
            data = response.json()
            print(f"  ✓ Pedido creado: {data.get('codigo', 'N/A')}")
            print(f"    Estado: {data.get('estado', 'N/A')}")
            print(f"    Tipo: {data.get('tipo_entrega', 'N/A')}")

        except httpx.ConnectError:
            pytest.skip("Conexión fallida al crear pedido (servidor no disponible).")
        except Exception as e:
            pytest.fail(f"Error creando pedido: {e}")


@pytest.mark.asyncio
async def test_billing_flow(access_token: str):
    """Prueba flujo de facturación"""
    print("\n💰 Probando flujo de facturación...")

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        print("  → Calculando tarifa...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/billing/calcular",
                json={
                    "tipo_entrega": "URBANA_RAPIDA",
                    "peso_kg": 2.5,
                    "distancia_km": 5.0
                },
                headers=headers,
                timeout=10.0
            )

            assert response.status_code == 200, f"Error calculando tarifa: {response.text}"
            data = response.json()
            print(f"  ✓ Tarifa calculada:")
            print(f"    Subtotal: ${data.get('subtotal', 'N/A')}")
            print(f"    Impuestos: ${data.get('impuestos', 'N/A')}")
            print(f"    Total: ${data.get('total', 'N/A')}")
            print(f"    Tiempo estimado: {data.get('tiempo_estimado_horas', 'N/A')} horas")

        except httpx.ConnectError:
            pytest.skip("Conexión fallida al calcular tarifa (servidor no disponible).")
        except Exception as e:
            pytest.fail(f"Error calculando tarifa: {e}")