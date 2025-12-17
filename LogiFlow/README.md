# LogiFlow - Plataforma Integral de Gestión de Operaciones para Delivery

## Descripción
LogiFlow es una plataforma centralizada y escalable basada en microservicios para gestionar operaciones de delivery multinivel de EntregaExpress S.A.

## Fase 1: Backend - Servicios REST y API Gateway

### Microservicios Implementados
1. **AuthService** (Puerto 5001) - Autenticación y autorización
2. **PedidoService** (Puerto 5002) - Gestión de pedidos
3. **FleetService** (Puerto 5003) - Gestión de flota y repartidores
4. **BillingService** (Puerto 5004) - Facturación básica
5. **API Gateway** (Puerto 5000) - Punto único de entrada

### Tecnologías Utilizadas
- **Python 3.11+**
- **FastAPI** - Framework web asíncrono
- **SQLAlchemy** - ORM para base de datos
- **PostgreSQL/SQLite** - Base de datos
- **JWT** - Autenticación basada en tokens
- **Pydantic** - Validación de esquemas
- **Uvicorn** - Servidor ASGI

### Requisitos
```bash
pip install -r requirements.txt
```

### Instalación

1. Clonar el repositorio
2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno (copiar .env.example a .env)

5. Inicializar bases de datos:
```bash
python scripts/init_db.py
```

### Ejecución (Docker + Kong)

#### Levantar toda la plataforma
```bash
docker compose up -d --build
```

- Proxy de Kong: http://localhost:8000
- Admin API de Kong: http://localhost:8001

Servicios detrás de Kong:
- AuthService: `http://localhost:8000/api/auth`
- PedidoService: `http://localhost:8000/api/pedidos`
- FleetService: `http://localhost:8000/api/flota`
- BillingService: `http://localhost:8000/api/billing`

Para detener:
```bash
docker compose down
```

### Documentación API
Con Docker, la documentación Swagger de cada servicio sigue disponible en sus puertos internos mapeados:
- **AuthService**: http://localhost:5001/docs
- **PedidoService**: http://localhost:5002/docs
- **FleetService**: http://localhost:5003/docs
- **BillingService**: http://localhost:5004/docs

El acceso productivo debe realizarse vía Kong por `http://localhost:8000`.

### Endpoints Principales

#### AuthService
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/login` - Autenticación
- `POST /api/auth/token/refresh` - Renovar token
- `POST /api/auth/token/revoke` - Revocar token

#### PedidoService
- `POST /api/pedidos` - Crear pedido
- `GET /api/pedidos` - Listar pedidos
- `GET /api/pedidos/{id}` - Obtener pedido
- `PATCH /api/pedidos/{id}` - Actualizar pedido
- `DELETE /api/pedidos/{id}` - Cancelar pedido

#### FleetService
- `POST /api/flota/repartidores` - Crear repartidor
- `GET /api/flota/repartidores` - Listar repartidores
- `GET /api/flota/repartidores/{id}` - Obtener repartidor
- `PATCH /api/flota/repartidores/{id}` - Actualizar repartidor
- `POST /api/flota/vehiculos` - Crear vehículo
- `GET /api/flota/vehiculos` - Listar vehículos

#### BillingService
- `POST /api/billing/calcular` - Calcular tarifa
- `POST /api/billing/facturas` - Generar factura
- `GET /api/billing/facturas/{id}` - Obtener factura

### Arquitectura

```
LogiFlow/
├── auth-service/       # Servicio de autenticación
├── pedido-service/     # Servicio de pedidos
├── fleet-service/      # Servicio de flota
├── billing-service/    # Servicio de facturación
├── api-gateway/        # API Gateway
├── shared/             # Código compartido
└── scripts/            # Scripts de utilidad
```

### Patrones de Diseño Implementados

1. **Factory Pattern** - Creación de tipos de vehículos y entregas
2. **Repository Pattern** - Acceso a datos
3. **Singleton Pattern** - Configuración de base de datos

### Roles y Permisos

- **ADMIN** - Administrador del sistema
- **GERENTE** - Gerente con acceso a métricas
- **SUPERVISOR** - Supervisor de zona
- **REPARTIDOR** - Repartidor (motorizado/vehículo/camión)
- **CLIENTE** - Cliente final

### Testing
```bash
pytest
```

### Autor
Proyecto integrador - Aplicaciones Distribuidas
Fecha: Diciembre 2025
