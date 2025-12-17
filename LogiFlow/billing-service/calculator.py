"""
Calculadora de tarifas usando las estrategias de entrega del PedidoService
"""
import sys

sys.path.append('..')
from shared.enums import TipoEntrega


class TarifaCalculator:
    """Calculadora de tarifas para diferentes tipos de entrega"""

    # Tasas de impuestos
    IVA_RATE = 0.12  # 12% IVA

    # Configuración por tipo de entrega (similar a factory.py del pedido-service)
    CONFIGURACION = {
        TipoEntrega.URBANA_RAPIDA: {
            "tarifa_base": 5.0,
            "costo_por_kg": 0.5,
            "costo_por_km": 0.8,
            "velocidad_promedio_kmh": 25.0
        },
        TipoEntrega.INTERMUNICIPAL: {
            "tarifa_base": 15.0,
            "costo_por_kg": 0.3,
            "costo_por_km": 1.2,
            "velocidad_promedio_kmh": 60.0
        },
        TipoEntrega.NACIONAL: {
            "tarifa_base": 50.0,
            "costo_por_kg": 0.15,
            "costo_por_km": 2.0,
            "velocidad_promedio_kmh": 50.0
        }
    }

    @classmethod
    def calcular_tarifa(cls, tipo_entrega: TipoEntrega, peso_kg: float,
                        distancia_km: float) -> dict:
        """
        Calcula la tarifa completa para una entrega
        
        Returns:
            dict con desglose de costos
        """
        if tipo_entrega not in cls.CONFIGURACION:
            raise ValueError(f"Tipo de entrega no soportado: {tipo_entrega}")

        config = cls.CONFIGURACION[tipo_entrega]

        # Calcular componentes
        tarifa_base = config["tarifa_base"]
        costo_peso = peso_kg * config["costo_por_kg"]
        costo_distancia = distancia_km * config["costo_por_km"]

        # Subtotal
        subtotal = tarifa_base + costo_peso + costo_distancia

        # Impuestos
        impuestos = round(subtotal * cls.IVA_RATE, 2)

        # Total
        total = round(subtotal + impuestos, 2)

        # Tiempo estimado
        tiempo_estimado_horas = round(
            distancia_km / config["velocidad_promedio_kmh"], 2)

        return {
            "tarifa_base": round(tarifa_base, 2),
            "costo_peso": round(costo_peso, 2),
            "costo_distancia": round(costo_distancia, 2),
            "subtotal": round(subtotal, 2),
            "impuestos": impuestos,
            "total": total,
            "tiempo_estimado_horas": tiempo_estimado_horas
        }
