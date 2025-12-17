from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List
import sys

sys.path.append('..')
from shared.enums import TipoVehiculo


class VehiculoEntrega(ABC):
    """
    Clase abstracta para vehículos de entrega
    
    Define el comportamiento común pero no es instanciable directamente.
    Las subclases concretas deben implementar los métodos abstractos.
    """

    def __init__(self, placa: str, marca: str, modelo: str, año: int):
        self.placa = placa
        self.marca = marca
        self.modelo = modelo
        self.año = año
        self._tipo_vehiculo = None

    @property
    @abstractmethod
    def capacidad_maxima_kg(self) -> float:
        """Capacidad máxima de carga en kilogramos"""
        pass

    @property
    @abstractmethod
    def velocidad_promedio_kmh(self) -> float:
        """Velocidad promedio del vehículo en km/h"""
        pass

    @property
    @abstractmethod
    def costo_operacional_por_km(self) -> float:
        """Costo operacional por kilómetro"""
        pass

    @property
    def tipo_vehiculo(self) -> TipoVehiculo:
        """Retorna el tipo de vehículo"""
        return self._tipo_vehiculo

    def calcular_tiempo_estimado(self, distancia_km: float) -> float:
        """
        Calcula el tiempo estimado de entrega en horas
        
        Template Method: usa velocidad_promedio_kmh de la subclase
        """
        return round(distancia_km / self.velocidad_promedio_kmh, 2)

    def calcular_costo_recorrido(self, distancia_km: float) -> float:
        """
        Calcula el costo del recorrido
        
        Template Method: usa costo_operacional_por_km de la subclase
        """
        return round(distancia_km * self.costo_operacional_por_km, 2)

    def puede_transportar(self, peso_kg: float) -> bool:
        """
        Verifica si el vehículo puede transportar un peso dado
        
        Template Method: usa capacidad_maxima_kg de la subclase
        """
        return peso_kg <= self.capacidad_maxima_kg

    def get_info(self) -> Dict:
        """Retorna información del vehículo"""
        return {
            "placa": self.placa,
            "marca": self.marca,
            "modelo": self.modelo,
            "año": self.año,
            "tipo":
            self.tipo_vehiculo.value if self.tipo_vehiculo else "DESCONOCIDO",
            "capacidad_maxima_kg": self.capacidad_maxima_kg,
            "velocidad_promedio_kmh": self.velocidad_promedio_kmh,
            "costo_operacional_por_km": self.costo_operacional_por_km
        }

    @abstractmethod
    def requiere_licencia_especial(self) -> bool:
        """Indica si requiere licencia especial"""
        pass


class Motorizado(VehiculoEntrega):
    """Vehículo tipo Motorizado (moto) - Entregas urbanas rápidas"""

    def __init__(self, placa: str, marca: str, modelo: str, año: int):
        super().__init__(placa, marca, modelo, año)
        self._tipo_vehiculo = TipoVehiculo.MOTORIZADO

    @property
    def capacidad_maxima_kg(self) -> float:
        return 20.0

    @property
    def velocidad_promedio_kmh(self) -> float:
        return 25.0

    @property
    def costo_operacional_por_km(self) -> float:
        return 0.30

    def requiere_licencia_especial(self) -> bool:
        return False  # Solo licencia tipo A


class VehiculoLiviano(VehiculoEntrega):
    """Vehículo Liviano (auto/camioneta) - Entregas intermunicipales"""

    def __init__(self, placa: str, marca: str, modelo: str, año: int):
        super().__init__(placa, marca, modelo, año)
        self._tipo_vehiculo = TipoVehiculo.VEHICULO_LIVIANO

    @property
    def capacidad_maxima_kg(self) -> float:
        return 200.0

    @property
    def velocidad_promedio_kmh(self) -> float:
        return 60.0

    @property
    def costo_operacional_por_km(self) -> float:
        return 0.50

    def requiere_licencia_especial(self) -> bool:
        return False  # Licencia tipo B regular


class Camion(VehiculoEntrega):
    """Camión (mediano/grande) - Entregas nacionales"""

    def __init__(self, placa: str, marca: str, modelo: str, año: int):
        super().__init__(placa, marca, modelo, año)
        self._tipo_vehiculo = TipoVehiculo.CAMION

    @property
    def capacidad_maxima_kg(self) -> float:
        return 5000.0

    @property
    def velocidad_promedio_kmh(self) -> float:
        return 50.0

    @property
    def costo_operacional_por_km(self) -> float:
        return 1.50

    def requiere_licencia_especial(self) -> bool:
        return True  # Requiere licencia tipo C o superior


class VehiculoFactory:
    """
    Factory Pattern para crear instancias de vehículos según tipo
    
    Centraliza la creación de objetos VehiculoEntrega
    """

    @staticmethod
    def crear_vehiculo(tipo: TipoVehiculo, placa: str, marca: str, modelo: str,
                       año: int) -> VehiculoEntrega:
        """
        Factory method para crear vehículos
        
        Args:
            tipo: Tipo de vehículo a crear
            placa: Placa del vehículo
            marca: Marca del vehículo
            modelo: Modelo del vehículo
            año: Año de fabricación
            
        Returns:
            Instancia de VehiculoEntrega correspondiente
            
        Raises:
            ValueError: Si el tipo de vehículo no es válido
        """
        if tipo == TipoVehiculo.MOTORIZADO:
            return Motorizado(placa, marca, modelo, año)
        elif tipo == TipoVehiculo.VEHICULO_LIVIANO:
            return VehiculoLiviano(placa, marca, modelo, año)
        elif tipo == TipoVehiculo.CAMION:
            return Camion(placa, marca, modelo, año)
        else:
            raise ValueError(f"Tipo de vehículo no soportado: {tipo}")

    @staticmethod
    def obtener_capacidades() -> Dict[TipoVehiculo, Dict]:
        """Retorna las capacidades de cada tipo de vehículo"""
        return {
            TipoVehiculo.MOTORIZADO: {
                "capacidad_kg": 20.0,
                "velocidad_kmh": 25.0,
                "costo_por_km": 0.30,
                "licencia_especial": False
            },
            TipoVehiculo.VEHICULO_LIVIANO: {
                "capacidad_kg": 200.0,
                "velocidad_kmh": 60.0,
                "costo_por_km": 0.50,
                "licencia_especial": False
            },
            TipoVehiculo.CAMION: {
                "capacidad_kg": 5000.0,
                "velocidad_kmh": 50.0,
                "costo_por_km": 1.50,
                "licencia_especial": True
            }
        }
