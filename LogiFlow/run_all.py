"""
Script para ejecutar todos los servicios simultáneamente
"""
import subprocess
import sys
import os
from pathlib import Path

# Obtener directorio raíz del proyecto
ROOT_DIR = Path(__file__).parent

# Configuración de servicios
SERVICES = [{
    "name": "AuthService",
    "dir": ROOT_DIR / "auth-service",
    "port": 5001,
    "module": "main:app"
}, {
    "name": "PedidoService",
    "dir": ROOT_DIR / "pedido-service",
    "port": 5002,
    "module": "main:app"
}, {
    "name": "FleetService",
    "dir": ROOT_DIR / "fleet-service",
    "port": 5003,
    "module": "main:app"
}, {
    "name": "BillingService",
    "dir": ROOT_DIR / "billing-service",
    "port": 5004,
    "module": "main:app"
}, {
    "name": "APIGateway",
    "dir": ROOT_DIR / "api-gateway",
    "port": 5000,
    "module": "main:app"
}]


def run_service(service):
    """Ejecuta un servicio individual"""
    print(f"\n🚀 Iniciando {service['name']} en puerto {service['port']}...")

    cmd = [
        sys.executable, "-m", "uvicorn", service["module"], "--host",
        "0.0.0.0", "--port",
        str(service["port"]), "--reload"
    ]

    return subprocess.Popen(cmd,
                            cwd=service["dir"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)


def main():
    """Ejecuta todos los servicios"""
    print("=" * 60)
    print("LogiFlow - Iniciando todos los microservicios")
    print("=" * 60)

    processes = []

    try:
        # Iniciar todos los servicios
        for service in SERVICES:
            process = run_service(service)
            processes.append((service["name"], process))

        print("\n" + "=" * 60)
        print("✅ Todos los servicios iniciados correctamente")
        print("=" * 60)
        print("\nServicios disponibles:")
        for service in SERVICES:
            print(f"  - {service['name']}: http://localhost:{service['port']}")
            print(f"    Docs: http://localhost:{service['port']}/docs")

        print("\n📝 API Gateway (punto de entrada): http://localhost:5000")
        print("📚 Documentación Gateway: http://localhost:5000/docs")
        print("\n⏸️  Presiona Ctrl+C para detener todos los servicios\n")

        # Esperar hasta que se interrumpa
        for name, process in processes:
            process.wait()

    except KeyboardInterrupt:
        print("\n\n🛑 Deteniendo todos los servicios...")

        for name, process in processes:
            print(f"   Deteniendo {name}...")
            process.terminate()

        # Esperar a que todos terminen
        for name, process in processes:
            process.wait()

        print("\n✅ Todos los servicios detenidos correctamente\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")

        for name, process in processes:
            process.terminate()

        sys.exit(1)


if __name__ == "__main__":
    main()
