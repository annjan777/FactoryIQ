import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, func

from modules.inventory.models import Inventory, StockMovement, InventoryReservation
from modules.inventory.schemas import InventoryAdjustment, ReservationCreate

class InventoryService:
    @staticmethod
    async def get_inventory_balance(
        db: AsyncSession,
        component_id: uuid.UUID,
        warehouse_id: uuid.UUID
    ) -> Optional[Inventory]:
        result = await db.execute(
            select(Inventory).where(
                Inventory.component_id == component_id,
                Inventory.warehouse_id == warehouse_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        adjustment: InventoryAdjustment,
        user_id: uuid.UUID
    ) -> Inventory:
        """
        Atomically adjusts inventory balances and records a movement.
        Enforces no negative inventory rule.
        """
        # 1. Row-level locking to prevent concurrency anomalies
        result = await db.execute(
            select(Inventory)
            .where(
                Inventory.component_id == adjustment.component_id,
                Inventory.warehouse_id == adjustment.warehouse_id
            )
            .with_for_update()
        )
        stock = result.scalar_one_or_none()
        
        # Resolve current tenant id
        tenant_context = await db.execute(text("SELECT current_setting('app.current_tenant', true)"))
        tenant_id_str = tenant_context.scalar()
        if not tenant_id_str:
            raise ValueError("Tenant context not initialized")
        tenant_id = uuid.UUID(tenant_id_str)

        if not stock:
            # Create a new record if it doesn't exist
            stock = Inventory(
                tenant_id=tenant_id,
                component_id=adjustment.component_id,
                warehouse_id=adjustment.warehouse_id,
                on_hand_qty=0.00,
                reserved_qty=0.00,
                allocated_qty=0.00,
                wip_qty=0.00,
                damaged_qty=0.00,
                in_transit_qty=0.00
            )
            db.add(stock)

        # Enforce movement logic
        if adjustment.movement_type == "grn":
            stock.on_hand_qty = float(stock.on_hand_qty) + float(adjustment.qty)
        elif adjustment.movement_type == "issue":
            if stock.available_qty < adjustment.qty:
                raise ValueError("Insufficient stock available to issue components")
            stock.on_hand_qty = float(stock.on_hand_qty) - float(adjustment.qty)
        elif adjustment.movement_type == "scrap":
            if float(stock.on_hand_qty) < adjustment.qty:
                raise ValueError("Insufficient on-hand stock to scrap")
            stock.on_hand_qty = float(stock.on_hand_qty) - float(adjustment.qty)
            stock.damaged_qty = float(stock.damaged_qty) + float(adjustment.qty)
        elif adjustment.movement_type == "adjustment":
            new_on_hand = float(stock.on_hand_qty) + float(adjustment.qty)
            if new_on_hand < 0:
                raise ValueError("Adjustment leads to negative physical inventory")
            stock.on_hand_qty = new_on_hand
        else:
            raise ValueError(f"Unknown movement type: {adjustment.movement_type}")

        # 2. Append to ledger
        movement = StockMovement(
            tenant_id=tenant_id,
            component_id=adjustment.component_id,
            warehouse_id=adjustment.warehouse_id,
            movement_type=adjustment.movement_type,
            qty=adjustment.qty,
            reference_type=adjustment.reference_type,
            reference_id=adjustment.reference_id,
            batch_no=adjustment.batch_no,
            lot_no=adjustment.lot_no,
            created_by=user_id
        )
        db.add(movement)
        await db.flush()
        
        return stock

    @staticmethod
    async def create_reservation(
        db: AsyncSession,
        res_in: ReservationCreate
    ) -> InventoryReservation:
        """
        Atomically reserve stock for a Sales / Production order.
        """
        # Lock stock row
        result = await db.execute(
            select(Inventory)
            .where(
                Inventory.component_id == res_in.component_id,
                Inventory.warehouse_id == res_in.warehouse_id
            )
            .with_for_update()
        )
        stock = result.scalar_one_or_none()
        
        tenant_context = await db.execute(text("SELECT current_setting('app.current_tenant', true)"))
        tenant_id_str = tenant_context.scalar()
        if not tenant_id_str:
            raise ValueError("Tenant context not initialized")
        tenant_id = uuid.UUID(tenant_id_str)

        if not stock or stock.available_qty < res_in.quantity:
            raise ValueError("Insufficient stock available for reservation")

        # Update balance
        stock.reserved_qty = float(stock.reserved_qty) + float(res_in.quantity)

        # Create Reservation record
        res = InventoryReservation(
            tenant_id=tenant_id,
            component_id=res_in.component_id,
            warehouse_id=res_in.warehouse_id,
            quantity=res_in.quantity,
            source_order_id=res_in.source_order_id,
            status="active",
            expires_at=res_in.expires_at
        )
        db.add(res)
        
        # Write movement log
        movement = StockMovement(
            tenant_id=tenant_id,
            component_id=res_in.component_id,
            warehouse_id=res_in.warehouse_id,
            movement_type="reserve",
            qty=-res_in.quantity, # Negative logic representation in stock movement
            reference_type="reservation",
            reference_id=None
        )
        db.add(movement)
        await db.flush()
        
        return res

    @staticmethod
    async def release_reservation(
        db: AsyncSession,
        reservation_id: uuid.UUID
    ) -> None:
        """
        Release a soft reservation and return quantities to the available pool.
        """
        # Fetch reservation
        result = await db.execute(
            select(InventoryReservation).where(InventoryReservation.id == reservation_id)
        )
        res = result.scalar_one_or_none()
        if not res or res.status != "active":
            raise ValueError("Active reservation not found")

        # Lock inventory row
        lock_result = await db.execute(
            select(Inventory)
            .where(
                Inventory.component_id == res.component_id,
                Inventory.warehouse_id == res.warehouse_id
            )
            .with_for_update()
        )
        stock = lock_result.scalar_one_or_none()
        if stock:
            # Rollback reserved quantity (prevent negative)
            stock.reserved_qty = max(0.00, float(stock.reserved_qty) - float(res.quantity))

        res.status = "cancelled"
        
        # Log to ledger
        movement = StockMovement(
            tenant_id=res.tenant_id,
            component_id=res.component_id,
            warehouse_id=res.warehouse_id,
            movement_type="release",
            qty=res.quantity,
            reference_type="reservation",
            reference_id=res.id
        )
        db.add(movement)
        await db.flush()

    @staticmethod
    async def transfer_stock(
        db: AsyncSession,
        from_warehouse_id: uuid.UUID,
        to_warehouse_id: uuid.UUID,
        component_id: uuid.UUID,
        qty: float,
        user_id: uuid.UUID
    ) -> List[Inventory]:
        """
        Atomically transfers stock from one warehouse to another, preventing concurrency race conditions.
        """
        if from_warehouse_id == to_warehouse_id:
            raise ValueError("Source and destination warehouses must be different")
        if qty <= 0:
            raise ValueError("Transfer quantity must be greater than zero")

        # Resolve current tenant id
        tenant_context = await db.execute(text("SELECT current_setting('app.current_tenant', true)"))
        tenant_id_str = tenant_context.scalar()
        if not tenant_id_str:
            raise ValueError("Tenant context not initialized")
        tenant_id = uuid.UUID(tenant_id_str)

        # 1. Pessimistic row locking on source warehouse inventory row
        source_result = await db.execute(
            select(Inventory)
            .where(
                Inventory.component_id == component_id,
                Inventory.warehouse_id == from_warehouse_id
            )
            .with_for_update()
        )
        source_stock = source_result.scalar_one_or_none()
        if not source_stock or source_stock.available_qty < qty:
            raise ValueError("Insufficient stock available in source warehouse for transfer")

        # 2. Pessimistic row locking on destination warehouse inventory row
        dest_result = await db.execute(
            select(Inventory)
            .where(
                Inventory.component_id == component_id,
                Inventory.warehouse_id == to_warehouse_id
            )
            .with_for_update()
        )
        dest_stock = dest_result.scalar_one_or_none()
        if not dest_stock:
            # Dynamically instantiate destination warehouse component ledger row if missing
            dest_stock = Inventory(
                tenant_id=tenant_id,
                component_id=component_id,
                warehouse_id=to_warehouse_id,
                on_hand_qty=0.00,
                reserved_qty=0.00,
                allocated_qty=0.00,
                wip_qty=0.00,
                damaged_qty=0.00,
                in_transit_qty=0.00
            )
            db.add(dest_stock)

        # 3. Deduct from source and add to destination
        source_stock.on_hand_qty = float(source_stock.on_hand_qty) - float(qty)
        dest_stock.on_hand_qty = float(dest_stock.on_hand_qty) + float(qty)

        # 4. Log movement records for source (transfer_out) and destination (transfer_in)
        movement_out = StockMovement(
            tenant_id=tenant_id,
            component_id=component_id,
            warehouse_id=from_warehouse_id,
            movement_type="transfer_out",
            qty=-qty,
            created_by=user_id
        )
        movement_in = StockMovement(
            tenant_id=tenant_id,
            component_id=component_id,
            warehouse_id=to_warehouse_id,
            movement_type="transfer_in",
            qty=qty,
            created_by=user_id
        )
        db.add(movement_out)
        db.add(movement_in)
        
        await db.flush()
        return [source_stock, dest_stock]
