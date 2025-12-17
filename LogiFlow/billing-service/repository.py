from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import models
import schemas
import calculator
import sys

sys.path.append('..')
from shared.enums import EstadoFactura, TipoEntrega


class BillingRepository:
    """Repository pattern for billing operations"""

    def __init__(self, db: Session):
        self.db = db

    def _generar_numero_factura(self) -> str:
        """Genera número único para factura (F-00001, F-00002, ...)"""
        ultima_factura = self.db.query(models.Factura).order_by(
            models.Factura.id.desc()).first()

        if not ultima_factura:
            numero = 1
        else:
            ultimo_numero = ultima_factura.numero_factura
            numero = int(ultimo_numero.split('-')[1]) + 1

        return f"F-{numero:05d}"

    def create_factura(self,
                       factura_data: schemas.FacturaCreate) -> models.Factura:
        """
        Crea una nueva factura - Transacción ACID
        
        Calcula automáticamente las tarifas usando TarifaCalculator
        """
        # Calcular tarifas
        calculo = calculator.TarifaCalculator.calcular_tarifa(
            factura_data.tipo_entrega, factura_data.peso_kg,
            factura_data.distancia_km)

        # Generar número de factura
        numero_factura = self._generar_numero_factura()

        # Crear factura
        db_factura = models.Factura(
            numero_factura=numero_factura,
            pedido_id=factura_data.pedido_id,
            cliente_id=factura_data.cliente_id,
            distancia_km=factura_data.distancia_km,
            peso_kg=factura_data.peso_kg,
            tipo_entrega=factura_data.tipo_entrega.value,
            tarifa_base=calculo["tarifa_base"],
            costo_peso=calculo["costo_peso"],
            costo_distancia=calculo["costo_distancia"],
            subtotal=calculo["subtotal"],
            impuestos=calculo["impuestos"],
            total=calculo["total"],
            estado=EstadoFactura.BORRADOR.value,
            notas=factura_data.notas)

        self.db.add(db_factura)
        self.db.commit()
        self.db.refresh(db_factura)

        return db_factura

    def get_factura_by_id(self, factura_id: int) -> Optional[models.Factura]:
        """Obtiene factura por ID"""
        return self.db.query(
            models.Factura).filter(models.Factura.id == factura_id).first()

    def get_factura_by_numero(self,
                              numero_factura: str) -> Optional[models.Factura]:
        """Obtiene factura por número"""
        return self.db.query(models.Factura).filter(
            models.Factura.numero_factura == numero_factura).first()

    def get_factura_by_pedido(self,
                              pedido_id: int) -> Optional[models.Factura]:
        """Obtiene factura por pedido_id"""
        return self.db.query(models.Factura).filter(
            models.Factura.pedido_id == pedido_id).first()

    def get_facturas(
            self,
            skip: int = 0,
            limit: int = 100,
            estado: Optional[EstadoFactura] = None,
            cliente_id: Optional[int] = None
    ) -> tuple[List[models.Factura], int]:
        """Obtiene lista de facturas con filtros"""
        query = self.db.query(models.Factura)

        if estado:
            query = query.filter(models.Factura.estado == estado.value)

        if cliente_id:
            query = query.filter(models.Factura.cliente_id == cliente_id)

        total = query.count()
        facturas = query.order_by(
            models.Factura.created_at.desc()).offset(skip).limit(limit).all()

        return facturas, total

    def update_factura(
            self, factura_id: int,
            update_data: schemas.FacturaUpdate) -> Optional[models.Factura]:
        """Actualiza factura - Transacción ACID"""
        db_factura = self.get_factura_by_id(factura_id)

        if not db_factura:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            if field == "estado":
                # Actualizar timestamps según estado
                if value == EstadoFactura.EMITIDA and not db_factura.emitida_at:
                    db_factura.emitida_at = datetime.utcnow()
                elif value == EstadoFactura.PAGADA and not db_factura.pagada_at:
                    db_factura.pagada_at = datetime.utcnow()
                elif value == EstadoFactura.ANULADA and not db_factura.anulada_at:
                    db_factura.anulada_at = datetime.utcnow()

                setattr(db_factura, field, value.value)
            else:
                setattr(db_factura, field, value)

        db_factura.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_factura)

        return db_factura
