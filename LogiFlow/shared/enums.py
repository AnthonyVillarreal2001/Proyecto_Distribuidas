from enum import Enum


class UserRole(str, Enum):
    """Roles de usuario en el sistema"""
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    SUPERVISOR = "SUPERVISOR"
    REPARTIDOR = "REPARTIDOR"
    CLIENTE = "CLIENTE"


class EstadoPedido(str, Enum):
    """Estados de un pedido"""
    RECIBIDO = "RECIBIDO"
    ASIGNADO = "ASIGNADO"
    EN_RUTA = "EN_RUTA"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class TipoEntrega(str, Enum):
    """Tipos de entrega disponibles"""
    URBANA_RAPIDA = "URBANA_RAPIDA"  # Última milla - motorizado
    INTERMUNICIPAL = "INTERMUNICIPAL"  # Vehículo liviano
    NACIONAL = "NACIONAL"  # Furgoneta o camión


class TipoVehiculo(str, Enum):
    """Tipos de vehículos"""
    MOTORIZADO = "MOTORIZADO"
    VEHICULO_LIVIANO = "VEHICULO_LIVIANO"
    CAMION = "CAMION"


class EstadoRepartidor(str, Enum):
    """Estados de disponibilidad del repartidor"""
    DISPONIBLE = "DISPONIBLE"
    EN_RUTA = "EN_RUTA"
    MANTENIMIENTO = "MANTENIMIENTO"
    INACTIVO = "INACTIVO"


class EstadoFactura(str, Enum):
    """Estados de factura"""
    BORRADOR = "BORRADOR"
    EMITIDA = "EMITIDA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"
