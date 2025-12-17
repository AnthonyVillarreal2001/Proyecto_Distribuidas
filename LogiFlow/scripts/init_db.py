"""
Script para inicializar todas las bases de datos
"""
import sys
from pathlib import Path

# Añadir directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from shared.database import Base, engine
from shared.config import get_settings

# Importar modelos de todos los servicios
from auth_service import models as auth_models
from pedido_service import models as pedido_models
from fleet_service import models as fleet_models
from billing_service import models as billing_models

settings = get_settings()


def init_database():
    """Inicializa la base de datos creando todas las tablas"""
    print("=" * 60)
    print("LogiFlow - Inicialización de Base de Datos")
    print("=" * 60)
    print(f"\nUsando base de datos: {settings.database_url}")

    try:
        # Crear todas las tablas
        print("\n📦 Creando tablas...")
        Base.metadata.create_all(bind=engine)

        print("\n✅ Tablas creadas exitosamente:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")

        print("\n" + "=" * 60)
        print("✅ Base de datos inicializada correctamente")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error al inicializar la base de datos: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
