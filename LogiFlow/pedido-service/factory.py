from abc import ABC, abstractmethod
from typing import Dict
import sys

sys.path.append('..')
from shared.enums import TipoEntrega, TipoVehiculo


class EntregaStrategy(ABC):
    """Clase abstracta para estrategias de entrega (patrón Strategy/Factory)"""

    @abstractmethod
    def get_tipo_vehiculo_requerido(self) -> TipoVehiculo:
        """Retorna el tipo de vehículo requerido para esta entrega"""
        pass

    @abstractmethod
    def validar_peso(self, peso_kg: float) -> bool:
        """Valida si el peso es válido para este tipo de entrega"""
        pass

    @abstractmethod
    def calcular_tarifa_base(self, peso_kg: float,
                             distancia_km: float) -> float:
        """Calcula la tarifa base según el tipo de entrega"""
        pass

    @abstractmethod
    def get_tiempo_estimado_horas(self, distancia_km: float) -> float:
        """Retorna el tiempo estimado de entrega en horas"""
        pass


class EntregaUrbanaRapida(EntregaStrategy):
    """Estrategia para entregas urbanas rápidas (última milla) - Motorizado"""

    PESO_MAX_KG = 20
    TARIFA_BASE = 5.0
    COSTO_POR_KG = 0.5
    COSTO_POR_KM = 0.8
    VELOCIDAD_PROMEDIO_KM_H = 25

    def get_tipo_vehiculo_requerido(self) -> TipoVehiculo:
        return TipoVehiculo.MOTORIZADO

    def validar_peso(self, peso_kg: float) -> bool:
        return 0 < peso_kg <= self.PESO_MAX_KG

    def calcular_tarifa_base(self, peso_kg: float,
                             distancia_km: float) -> float:
        tarifa = self.TARIFA_BASE
        tarifa += peso_kg * self.COSTO_POR_KG
        tarifa += distancia_km * self.COSTO_POR_KM
        return round(tarifa, 2)

    def get_tiempo_estimado_horas(self, distancia_km: float) -> float:
        return round(distancia_km / self.VELOCIDAD_PROMEDIO_KM_H, 2)


class EntregaIntermunicipal(EntregaStrategy):
    """Estrategia para entregas intermunicipales - Vehículo Liviano"""

    PESO_MAX_KG = 200
    TARIFA_BASE = 15.0
    COSTO_POR_KG = 0.3
    COSTO_POR_KM = 1.2
    VELOCIDAD_PROMEDIO_KM_H = 60

    def get_tipo_vehiculo_requerido(self) -> TipoVehiculo:
        return TipoVehiculo.VEHICULO_LIVIANO

    def validar_peso(self, peso_kg: float) -> bool:
        return 0 < peso_kg <= self.PESO_MAX_KG

    def calcular_tarifa_base(self, peso_kg: float,
                             distancia_km: float) -> float:
        tarifa = self.TARIFA_BASE
        tarifa += peso_kg * self.COSTO_POR_KG
        tarifa += distancia_km * self.COSTO_POR_KM
        return round(tarifa, 2)

    def get_tiempo_estimado_horas(self, distancia_km: float) -> float:
        return round(distancia_km / self.VELOCIDAD_PROMEDIO_KM_H, 2)


class EntregaNacional(EntregaStrategy):
    """Estrategia para entregas nacionales - Camión"""

    PESO_MAX_KG = 5000
    TARIFA_BASE = 50.0
    COSTO_POR_KG = 0.15
    COSTO_POR_KM = 2.0
    VELOCIDAD_PROMEDIO_KM_H = 50

    def get_tipo_vehiculo_requerido(self) -> TipoVehiculo:
        return TipoVehiculo.CAMION

    def validar_peso(self, peso_kg: float) -> bool:
        return 0 < peso_kg <= self.PESO_MAX_KG

    def calcular_tarifa_base(self, peso_kg: float,
                             distancia_km: float) -> float:
        tarifa = self.TARIFA_BASE
        tarifa += peso_kg * self.COSTO_POR_KG
        tarifa += distancia_km * self.COSTO_POR_KM
        return round(tarifa, 2)

    def get_tiempo_estimado_horas(self, distancia_km: float) -> float:
        return round(distancia_km / self.VELOCIDAD_PROMEDIO_KM_H, 2)


class EntregaFactory:
    """Factory Pattern para crear estrategias de entrega"""

    _strategies: Dict[TipoEntrega, EntregaStrategy] = {
        TipoEntrega.URBANA_RAPIDA: EntregaUrbanaRapida(),
        TipoEntrega.INTERMUNICIPAL: EntregaIntermunicipal(),
        TipoEntrega.NACIONAL: EntregaNacional()
    }

    @classmethod
    def crear_estrategia(cls, tipo_entrega: TipoEntrega) -> EntregaStrategy:
        """
        Factory method para crear estrategia de entrega según tipo
        
        Args:
            tipo_entrega: Tipo de entrega solicitada
            
        Returns:
            EntregaStrategy correspondiente
            
        Raises:
            ValueError: Si el tipo de entrega no es válido
        """
        if tipo_entrega not in cls._strategies:
            raise ValueError(f"Tipo de entrega no soportado: {tipo_entrega}")

        return cls._strategies[tipo_entrega]

    @classmethod
    def validar_pedido(cls, tipo_entrega: TipoEntrega,
                       peso_kg: float) -> tuple[bool, str]:
        """
        Valida si un pedido puede ser procesado con el tipo de entrega especificado
        
        Returns:
            (valido, mensaje_error)
        """
        try:
            estrategia = cls.crear_estrategia(tipo_entrega)

            if not estrategia.validar_peso(peso_kg):
                peso_max = {
                    TipoEntrega.URBANA_RAPIDA: 20,
                    TipoEntrega.INTERMUNICIPAL: 200,
                    TipoEntrega.NACIONAL: 5000
                }[tipo_entrega]

                return False, f"Peso excede el máximo permitido para {tipo_entrega.value} ({peso_max} kg)"

            return True, ""

        except ValueError as e:
            return False, str(e)
