import uuid
import re
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from modules.sales.service import FeasibilityService
from modules.sales.models import SalesOrder
from modules.auth.models import User
from modules.inventory.models import Inventory
from modules.bom.models import Component
from modules.ai_assistant.hallucination_gate import HallucinationGate

class AIAssistantService:
    SLM_URL = "http://localhost:11434/api/generate" # Default local Ollama endpoint

    @staticmethod
    def _fallback_intent_classifier(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Regex-based rule engine to classify intent and extract slots when the SLM is offline.
        Supports fuzzy name mapping, standard order digits formatting, and context-carrying.
        """
        message_lower = message.lower()
        context = context or {}
        
        # 1. Extract Order Reference
        order_match = re.search(r'so-[a-zA-Z0-9\-]+', message_lower)
        order_no = None
        if order_match:
            order_no = order_match.group(0).upper()
        else:
            # Match digit references (e.g., 'order 1024' or 'order #1024')
            order_digit_match = re.search(r'order\s*(?:#|\s)?\s*([0-9a-zA-Z\-]+)', message_lower)
            if order_digit_match:
                digit_ref = order_digit_match.group(1).upper()
                order_no = digit_ref if digit_ref.startswith("SO-") else f"SO-{digit_ref}"
        
        # Pronoun/Context resolution for order check (pronouns like "it", "the order")
        if not order_no and any(k in message_lower for k in ["fulfill", "complete", "ready", "the order", "it"]):
            order_no = context.get("order_no") or context.get("active_order")

        # 2. Extract Component Code Reference (standardizing fuzzy names to database keys)
        component_code = None
        comp_keywords = ["front", "back", "sleeve", "collar", "label", "comp-"]
        if any(kw in message_lower for kw in comp_keywords):
            if "front" in message_lower:
                component_code = "FRONT-PANEL"
            elif "back" in message_lower:
                component_code = "BACK-PANEL"
            elif "sleeve" in message_lower:
                component_code = "SLEEVE"
            elif "collar" in message_lower:
                component_code = "COLLAR"
            elif "label" in message_lower:
                component_code = "LABEL"
            else:
                # Try finding standard COMP-XXXX matches
                comp_code_match = re.search(r'comp-[a-zA-Z0-9\-]+', message_lower)
                if comp_code_match:
                    component_code = comp_code_match.group(0).upper()

        if not component_code:
            component_code = context.get("component_code") or context.get("active_component")

        # 3. Classify Action: Create PO
        is_purchase = any(k in message_lower for k in ["buy", "purchase", "procure", "replenish", "shortfall", "missing", "requisition"]) or (
            "order" in message_lower and any(k in message_lower for k in ["shortages", "shortfall", "panels", "sleeves", "collars", "labels", "need", "generate", "create"])
        )
        if is_purchase:
            # Extract optional explicit quantity
            qty = None
            qty_match = re.search(r'\b\d{2,}\b', message_lower)
            if qty_match:
                qty = float(qty_match.group(0))
            return {
                "intent": "create_po",
                "entities": {
                    "order_no": order_no,
                    "component_code": component_code,
                    "qty": qty
                },
                "confidence": 0.95
            }

        # 4. Classify Action: Transition Work Order Stage
        is_transition = any(k in message_lower for k in ["start", "complete", "finish", "advance", "transition", "stage", "step", "work order"]) or any(s in message_lower for s in ["cutting", "stitching", "finishing", "packing"])
        if is_transition:
            stage = None
            for s in ["cutting", "stitching", "finishing", "packing"]:
                if s in message_lower:
                    stage = s
                    break
            target_status = "active"
            if any(k in message_lower for k in ["complete", "finish", "done", "completed"]):
                target_status = "completed"
            return {
                "intent": "transition_work_order",
                "entities": {
                    "stage": stage,
                    "target_status": target_status
                },
                "confidence": 0.95
            }

        # 5. Classify Intents based on vocabulary
        is_feasibility = any(k in message_lower for k in ["feasibility", "fulfill", "complete", "ready", "can i build", "can we build"])
        if is_feasibility or (order_no and not component_code):
            return {
                "intent": "check_feasibility",
                "entities": {"order_no": order_no},
                "confidence": 0.90
            }

        is_inventory = any(k in message_lower for k in ["stock", "inventory", "on hand", "how many", "count", "do we have", "quantity", "available"])
        if is_inventory or component_code:
            return {
                "intent": "inventory_lookup",
                "entities": {"component_code": component_code},
                "confidence": 0.85
            }

        return {
            "intent": "unknown",
            "entities": {},
            "confidence": 1.0
        }

    @classmethod
    async def classify_intent(cls, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Classifies user intent using the local SLM, falling back to regex.
        """
        system_prompt = (
            "You are an intent parser for a manufacturing ERP. Output ONLY valid JSON matching: "
            '{"intent": "<one of: check_feasibility|inventory_lookup|create_po|transition_work_order|unknown>", '
            '"entities": {"order_no": string|null, "component_code": string|null, "qty": float|null, "stage": string|null, "target_status": string|null}, "confidence": float}'
        )
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    cls.SLM_URL,
                    json={
                        "model": "qwen2.5:3b-instruct",
                        "prompt": f"System: {system_prompt}\nUser Query: {message}\nAssistant:",
                        "format": "json",
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    import json
                    return json.loads(response.json()["response"])
        except Exception:
            # Fallback quietly to regex parser on connection issues
            pass
            
        return cls._fallback_intent_classifier(message, context)

    @classmethod
    async def route_and_execute(
        cls, 
        db: AsyncSession, 
        intent_info: Dict[str, Any],
        current_user: User
    ) -> Dict[str, Any]:
        """
        Resolves the intent into transactional database calls.
        """
        intent = intent_info.get("intent", "unknown")
        entities = intent_info.get("entities", {})

        # Import modules dynamically to prevent circular dependencies
        from modules.purchasing.models import Supplier, PurchaseOrder, PurchaseOrderLine
        from modules.production.models import ProductionOrder, WorkOrder
        from modules.bom.models import Warehouse
        from modules.sales.models import SalesOrderLine
        from modules.inventory.models import InventoryReservation, StockMovement
        from modules.inventory.service import InventoryService
        import random

        if intent == "create_po":
            # 1. Fetch default Supplier and Warehouse
            sup_res = await db.execute(select(Supplier))
            supplier = sup_res.scalars().first()
            wh_res = await db.execute(select(Warehouse))
            warehouse = wh_res.scalars().first()

            if not supplier or not warehouse:
                return {"error": "Missing supplier or warehouse registrations."}

            po_lines = []

            # Case A: Specific single component purchase
            comp_code = entities.get("component_code")
            if comp_code:
                comp_res = await db.execute(select(Component).where(Component.code.ilike(comp_code)))
                comp = comp_res.scalar_one_or_none()
                if not comp:
                    return {"error": f"Component {comp_code} not found."}
                qty = entities.get("qty") or 100.0 # Default fallback amount
                po_lines.append((comp.id, qty))
            
            # Case B: Order all shortages from feasibility check
            else:
                order_no = entities.get("order_no")
                if not order_no:
                    return {"error": "Missing order reference to calculate shortages."}
                so_res = await db.execute(select(SalesOrder).where(SalesOrder.order_no.ilike(order_no)))
                so = so_res.scalar_one_or_none()
                if not so:
                    return {"error": f"Sales Order {order_no} not found."}
                
                feasibility = await FeasibilityService.evaluate_order(db=db, sales_order_id=so.id)
                if not feasibility.recommended_purchase_orders:
                    return {"error": "No shortfalls detected. Stock is fully feasible."}
                
                for recommend in feasibility.recommended_purchase_orders:
                    po_lines.append((recommend.component_id, recommend.qty))

            # Generate PO record
            po_no = f"PO-{random.randint(1000, 9999)}"
            po = PurchaseOrder(
                tenant_id=current_user.tenant_id,
                org_id=current_user.org_id,
                supplier_id=supplier.id,
                po_no=po_no,
                status="draft"
            )
            db.add(po)
            await db.flush()

            for c_id, q in po_lines:
                pol = PurchaseOrderLine(
                    tenant_id=current_user.tenant_id,
                    po_id=po.id,
                    component_id=c_id,
                    qty_ordered=q,
                    unit_cost=4.50
                )
                db.add(pol)

            await db.commit()
            return {"po_no": po.po_no, "status": po.status, "lines_count": len(po_lines)}

        elif intent == "transition_work_order":
            stage = entities.get("stage")
            target_status = entities.get("target_status") or "active"

            if not stage:
                return {"error": "Missing stage identifier (cutting, stitching, finishing, packing)."}

            # Find active work order
            wo_res = await db.execute(
                select(WorkOrder)
                .join(ProductionOrder)
                .options(selectinload(WorkOrder.production_order))
                .where(WorkOrder.stage == stage)
                .where(ProductionOrder.status != "completed")
                .order_by(ProductionOrder.created_at.desc())
            )
            wo = wo_res.scalars().first()
            if not wo:
                return {"error": f"No active production run found for stage: {stage}."}

            po = wo.production_order

            if target_status == "active":
                if wo.status != "pending":
                    return {"error": f"Work order {stage} is already {wo.status}."}
                wo.status = "active"
                if po.status == "scheduled":
                    po.status = "wip"

            elif target_status == "completed":
                if wo.status != "active":
                    return {"error": f"Work order {stage} must be active to complete."}
                wo.status = "completed"

                if wo.sequence_no == 4:
                    po.status = "completed"

                    # Consume reservations
                    res_query = await db.execute(
                        select(InventoryReservation)
                        .where(InventoryReservation.source_order_id == po.id, InventoryReservation.status == "active")
                    )
                    reservations = res_query.scalars().all()

                    for r in reservations:
                        r.status = "completed"
                        stock_res = await db.execute(
                            select(Inventory)
                            .where(Inventory.component_id == r.component_id, Inventory.warehouse_id == r.warehouse_id)
                            .with_for_update()
                        )
                        stock = stock_res.scalar_one()
                        stock.on_hand_qty = float(stock.on_hand_qty) - float(r.quantity)
                        stock.reserved_qty = float(stock.reserved_qty) - float(r.quantity)

                        db.add(
                            StockMovement(
                                tenant_id=r.tenant_id,
                                component_id=r.component_id,
                                warehouse_id=r.warehouse_id,
                                movement_type="adjustment",
                                qty=-r.quantity,
                                reference_type="production_order",
                                reference_id=po.id,
                                created_by=current_user.id
                            )
                        )

                    # Update Sales order
                    if po.sales_order_id:
                        sol_res = await db.execute(
                            select(SalesOrderLine)
                            .where(SalesOrderLine.sales_order_id == po.sales_order_id, SalesOrderLine.product_id == po.product_id)
                        )
                        so_line = sol_res.scalar_one_or_none()
                        if so_line:
                            so_line.qty_produced = float(so_line.qty_produced or 0.0) + float(po.target_qty)
                            
                            so_q = await db.execute(
                                select(SalesOrder).options(selectinload(SalesOrder.lines)).where(SalesOrder.id == po.sales_order_id)
                            )
                            so = so_q.scalar_one()
                            all_complete = all(float(line.qty_produced) >= float(line.qty_ordered) for line in so.lines)
                            so.status = "fulfilled" if all_complete else "partially_produced"

            await db.commit()
            return {"stage": stage, "status": wo.status, "production_order_status": po.status}

        elif intent == "check_feasibility":
            order_no = entities.get("order_no")
            if not order_no:
                return {"error": "Missing order reference parameter."}
                
            # Find order UUID from order_no
            query = select(SalesOrder).where(SalesOrder.order_no.ilike(order_no))
            res = await db.execute(query)
            so = res.scalar_one_or_none()
            if not so:
                return {"error": f"Sales Order {order_no} not found."}
                
            feasibility = await FeasibilityService.evaluate_order(db=db, sales_order_id=so.id)
            return feasibility.model_dump()

        elif intent == "inventory_lookup":
            comp_code = entities.get("component_code")
            if not comp_code:
                return {"error": "Missing component identifier parameter."}
                
            # Fetch component info
            query = select(Component).where(Component.code.ilike(comp_code))
            res = await db.execute(query)
            comp = res.scalar_one_or_none()
            if not comp:
                return {"error": f"Component {comp_code} not found."}
                
            # Query balance sum
            inv_query = select(func.sum(Inventory.on_hand_qty), func.sum(Inventory.reserved_qty))\
                .where(Inventory.component_id == comp.id)
            inv_res = await db.execute(inv_query)
            on_hand, reserved = inv_res.first() or (0.00, 0.00)
            
            on_hand = float(on_hand or 0.00)
            reserved = float(reserved or 0.00)
            available = on_hand - reserved
            
            return {
                "component_code": comp.code,
                "component_name": comp.name,
                "on_hand": on_hand,
                "reserved": reserved,
                "available": available,
                "uom": comp.uom
            }

        return {"error": "Unable to map request to backend functions."}

    @classmethod
    def _generate_fallback_narrative(cls, intent: str, data: Dict[str, Any]) -> str:
        """
        Secure Jinja2 style formatters guaranteeing zero mathematical hallucinations.
        """
        if "error" in data:
            return data["error"]

        if intent == "create_po":
            return f"Successfully generated draft Purchase Order {data['po_no']} for missing components (contains {data['lines_count']} lines)."

        elif intent == "transition_work_order":
            return f"Transitioned stage {data['stage']} to {data['status']}. Production run status is now {data['production_order_status']}."

        elif intent == "check_feasibility":
            limiting = ", ".join([c["component_name"] for c in data.get("limiting_components", [])])
            if data["shortfall_qty"] == 0:
                return (
                    f"Order feasibility is 100%. All {data['requested_qty']} garments can "
                    "be manufactured immediately using available stock."
                )
            else:
                return (
                    f"Order is currently blocked. You can immediately manufacture {data['producible_qty']} "
                    f"garments out of {data['requested_qty']} requested (Readiness: {data['readiness_pct']}%). "
                    f"The main production bottleneck is {limiting}. "
                    f"A purchase suggestion has been created to acquire missing components."
                )

        elif intent == "inventory_lookup":
            return (
                f"Component {data['component_code']} ({data['component_name']}) has "
                f"{data['on_hand']} {data['uom']} on hand, with {data['reserved']} reserved. "
                f"Available pool: {data['available']} {data['uom']}."
            )

        return "I processed your request, but could not compose a natural summary. Please check the data logs below."

    @classmethod
    async def compose_response(
        cls, 
        intent: str, 
        data: Dict[str, Any]
    ) -> str:
        """
        Generates narrative from the local SLM, validating via HallucinationGate,
        falling back to deterministic text if checks fail.
        """
        fallback_text = cls._generate_fallback_narrative(intent, data)
        if "error" in data:
            return fallback_text
            
        system_prompt = (
            "You are an ERP assistant narrating database facts. Write a short, fluent sentence based ONLY on the "
            "supplied JSON data values. Never invent numbers, dates, or quantities that are not explicitly present."
        )
        
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.post(
                    cls.SLM_URL,
                    json={
                        "model": "qwen2.5:3b-instruct",
                        "prompt": f"System: {system_prompt}\nJSON Data: {data}\nAssistant Narrative:",
                        "stream": False
                    }
                )
                if response.status_code == 200:
                    slm_text = response.json()["response"].strip()
                    # Verify text numbers against facts to block hallucination
                    if HallucinationGate.verify_grounding(slm_text, data):
                        return slm_text
        except Exception:
            pass
            
        return fallback_text
