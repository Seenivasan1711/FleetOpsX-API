"""
PlanningChatAgent — AI-1 E8.

Conversational replan agent. Activated when an OPEN planning session exists.
Provides 6 LangChain tools to let dispatchers query and mutate the live plan
via natural language chat.

Chat history is stored in the ChatMessage table (PostgreSQL) with
session_id = "planning_<planning_session_id>" to namespace from regular chat.

Tool loop: LLM → tool_calls? → execute → re-invoke → ... → final answer.
Max iterations: 4 (prevents runaway loops).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime
from typing import Any
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.planning_session import PlanningSession

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 4
_HISTORY_WINDOW = 8  # message pairs

_SYSTEM_PLANNING = """You are FleetOpsX Planning Assistant, an AI helping fleet dispatchers refine today's delivery plan.

An OPEN planning session is active for {plan_date}.
Active plan ID: {plan_id}

You have access to tools to:
- View the current plan assignments
- Check driver capacity and time-window feasibility before making changes
- Move orders between drivers
- Flag drivers for overtime review
- Explain any planning constraint

When making changes, always check feasibility first, then apply. Summarise every change you make.
Be concise, factual, and action-oriented. If you cannot satisfy a request safely, explain why.

{instructions_block}"""

_FALLBACK_REPLY = (
    "Planning chat is not available — no LLM API key is configured for your tenant. "
    "Set llm_provider and llm_api_key via Tenant Settings."
)

# ─── Chat history helpers ──────────────────────────────────────────────────────

def _chat_key(planning_session_id: str) -> str:
    return f"planning_{planning_session_id}"


def _save_messages(db: Session, tenant_id: UUID, planning_session_id: str, user_text: str, reply_text: str) -> None:
    key = _chat_key(planning_session_id)
    db.add(ChatMessage(tenant_id=tenant_id, session_id=key, role="user", content=user_text))
    db.add(ChatMessage(tenant_id=tenant_id, session_id=key, role="assistant", content=reply_text))
    db.commit()


def _load_history(db: Session, tenant_id: UUID, planning_session_id: str) -> list[ChatMessage]:
    key = _chat_key(planning_session_id)
    rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.tenant_id == tenant_id, ChatMessage.session_id == key)
        .order_by(ChatMessage.created_at.desc())
        .limit(_HISTORY_WINDOW * 2)
    ).scalars().all()
    return rows[::-1]  # chronological


def get_planning_history(db: Session, tenant_id: str, planning_session_id: str) -> list[ChatMessage]:
    tid = UUID(tenant_id)
    key = _chat_key(planning_session_id)
    return db.execute(
        select(ChatMessage)
        .where(ChatMessage.tenant_id == tid, ChatMessage.session_id == key)
        .order_by(ChatMessage.created_at.asc())
        .limit(100)
    ).scalars().all()


# ─── Session lookup ────────────────────────────────────────────────────────────

def get_open_session(db: Session, tenant_id: str, plan_date: date) -> PlanningSession | None:
    return db.execute(
        select(PlanningSession).where(
            PlanningSession.tenant_id == UUID(tenant_id),
            PlanningSession.plan_date == plan_date,
            PlanningSession.status == "OPEN",
        )
    ).scalar_one_or_none()


# ─── Tool factory ──────────────────────────────────────────────────────────────

def _make_tools(db: Session, tenant_id: str, session: PlanningSession, llm: Any) -> list:
    """Return LangChain @tool functions closed over the current DB session and plan."""
    tid = UUID(tenant_id)
    plan_id: UUID | None = session.active_plan_id

    @tool
    def get_current_plan(include_stops: bool = False) -> str:
        """
        Get a summary of the current active plan — assignments, driver order counts,
        and top-level statistics (total orders, assigned, distance).
        Set include_stops=true for a full stop listing per route.
        """
        try:
            from app.models.route_plan import RoutePlan, Route, RouteStop
            from sqlalchemy.orm import joinedload

            if not plan_id:
                return "No active plan found for this session."

            plan = db.execute(
                select(RoutePlan)
                .where(RoutePlan.id == plan_id, RoutePlan.tenant_id == tid)
                .options(
                    joinedload(RoutePlan.routes).joinedload(Route.stops),
                    joinedload(RoutePlan.routes).joinedload(Route.driver),
                )
            ).scalar_one_or_none()

            if not plan:
                return "Plan not found."

            lines = [
                f"Plan {plan.id} | Date: {plan.plan_date} | Status: {plan.status}",
                f"Orders: {plan.assigned_orders}/{plan.total_orders} assigned | Routes: {plan.total_routes}",
                f"Savings: {plan.km_saved or 0:.1f} km / {plan.hrs_saved or 0:.2f} hrs",
                "",
                "Routes:",
            ]
            for route in plan.routes:
                driver_name = route.driver.full_name if route.driver else "(no driver)"
                stops_count = len(route.stops)
                lines.append(f"  Driver: {driver_name} ({route.driver_id}) — {stops_count} stops, "
                              f"{route.estimated_distance_km or 0:.1f} km")
                if include_stops:
                    for stop in sorted(route.stops, key=lambda s: s.sequence):
                        lines.append(f"    [{stop.sequence}] order={stop.order_id} status={stop.status} "
                                     f"eta={stop.estimated_arrival or 'N/A'}")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("get_current_plan tool error: %s", exc)
            return f"Error retrieving plan: {exc}"

    @tool
    def check_driver_capacity(driver_id: str, additional_stops: int = 1) -> str:
        """
        Check whether a driver can take on additional_stops more stops.
        Compares current stop count vs vehicle capacity_units.
        Returns capacity status and headroom.
        """
        try:
            from app.models.route_plan import Route, RouteStop
            from sqlalchemy.orm import joinedload

            if not plan_id:
                return "No active plan."

            route = db.execute(
                select(Route)
                .where(
                    Route.plan_id == plan_id,
                    Route.driver_id == UUID(driver_id),
                    Route.tenant_id == tid,
                )
                .options(joinedload(Route.stops), joinedload(Route.vehicle))
            ).scalar_one_or_none()

            if not route:
                return f"Driver {driver_id} has no route in the current plan."

            current_stops = len(route.stops)
            vehicle = route.vehicle
            capacity = vehicle.capacity_units if vehicle and vehicle.capacity_units else None
            driver_name = route.driver.full_name if route.driver else driver_id

            if capacity is None:
                return (
                    f"Driver {driver_name}: {current_stops} stops assigned. "
                    f"Vehicle has no unit capacity limit — {additional_stops} more stop(s) are feasible."
                )

            new_total = current_stops + additional_stops
            headroom = capacity - current_stops
            status = "OK" if new_total <= capacity else "OVER_CAPACITY"
            return (
                f"Driver {driver_name}: {current_stops}/{capacity} stops (headroom={headroom}). "
                f"Adding {additional_stops} → {new_total} stops — status: {status}."
            )
        except Exception as exc:
            logger.warning("check_driver_capacity tool error: %s", exc)
            return f"Error checking capacity: {exc}"

    @tool
    def check_time_window_feasibility(order_id: str, driver_id: str) -> str:
        """
        Check whether reassigning order_id to driver_id is feasible given the order's
        time window and the driver's current estimated route duration.
        Returns a feasibility verdict with reasoning.
        """
        try:
            from app.models.order import Order
            from app.models.route_plan import Route, RouteStop

            order = db.execute(
                select(Order).where(Order.id == UUID(order_id), Order.tenant_id == tid)
            ).scalar_one_or_none()
            if not order:
                return f"Order {order_id} not found."

            tw_start = order.time_window_start
            tw_end = order.time_window_end

            if not tw_start and not tw_end:
                return f"Order {order_id} has no time window — reassignment is always feasible."

            route = db.execute(
                select(Route)
                .where(
                    Route.plan_id == plan_id,
                    Route.driver_id == UUID(driver_id),
                    Route.tenant_id == tid,
                )
            ).scalar_one_or_none()

            if not route:
                return f"Driver {driver_id} has no active route in the current plan."

            stop_count = db.execute(
                select(RouteStop)
                .where(RouteStop.route_id == route.id)
            ).scalars().count() if False else len(
                db.execute(select(RouteStop).where(RouteStop.route_id == route.id)).scalars().all()
            )

            est_min = route.estimated_duration_minutes or 0
            tw_str = ""
            if tw_start:
                tw_str += f"window_start={tw_start}"
            if tw_end:
                tw_str += f" window_end={tw_end}"

            verdict = "FEASIBLE" if est_min < 480 else "TIGHT"
            return (
                f"Order {order_id}: {tw_str}. "
                f"Driver {driver_id} currently has {stop_count} stops, "
                f"est. duration {est_min:.0f} min. Verdict: {verdict} "
                f"(manual review recommended if route duration > 8h)."
            )
        except Exception as exc:
            logger.warning("check_time_window_feasibility tool error: %s", exc)
            return f"Error checking time window: {exc}"

    @tool
    def move_order(order_id: str, from_driver_id: str, to_driver_id: str, reason: str) -> str:
        """
        Move order_id from from_driver_id's route to to_driver_id's route in the current plan.
        Creates an OverrideLog audit record. Appends the stop to the end of the destination route.
        Returns a confirmation or error.
        """
        try:
            from app.models.route_plan import Route, RouteStop
            from app.models.override_log import OverrideLog

            if not plan_id:
                return "No active plan — cannot move order."

            from_route = db.execute(
                select(Route).where(
                    Route.plan_id == plan_id,
                    Route.driver_id == UUID(from_driver_id),
                    Route.tenant_id == tid,
                )
            ).scalar_one_or_none()

            to_route = db.execute(
                select(Route).where(
                    Route.plan_id == plan_id,
                    Route.driver_id == UUID(to_driver_id),
                    Route.tenant_id == tid,
                )
            ).scalar_one_or_none()

            if not from_route:
                return f"Driver {from_driver_id} has no route in the current plan."
            if not to_route:
                return f"Driver {to_driver_id} has no route in the current plan."

            stop = db.execute(
                select(RouteStop).where(
                    RouteStop.route_id == from_route.id,
                    RouteStop.order_id == UUID(order_id),
                )
            ).scalar_one_or_none()

            if not stop:
                return f"Order {order_id} is not assigned to driver {from_driver_id}."

            # Determine next sequence number in to_route
            existing_stops = db.execute(
                select(RouteStop).where(RouteStop.route_id == to_route.id)
            ).scalars().all()
            next_seq = max((s.sequence for s in existing_stops), default=0) + 1

            # Reassign
            stop.route_id = to_route.id
            stop.sequence = next_seq

            # Update stop counts
            from_route.total_stops = max(0, (from_route.total_stops or 1) - 1)
            to_route.total_stops = (to_route.total_stops or 0) + 1

            # Audit log
            db.add(OverrideLog(
                id=uuid.uuid4(),
                tenant_id=tid,
                session_id=session.id,
                plan_id=plan_id,
                override_type="MOVE_ORDER",
                reason_text=reason or "",
                payload={
                    "order_id": order_id,
                    "from_driver_id": from_driver_id,
                    "to_driver_id": to_driver_id,
                    "from_route_id": str(from_route.id),
                    "to_route_id": str(to_route.id),
                    "new_sequence": next_seq,
                },
            ))

            db.commit()
            return (
                f"Order {order_id} moved from driver {from_driver_id} to {to_driver_id} "
                f"(sequence {next_seq}). OverrideLog created. Reason: {reason}"
            )
        except Exception as exc:
            db.rollback()
            logger.warning("move_order tool error: %s", exc)
            return f"Error moving order: {exc}"

    @tool
    def flag_overtime(driver_id: str, reason: str) -> str:
        """
        Flag a driver for overtime review. Creates an AgentSuggestion record visible
        in the Dispatcher UI suggestions panel. Returns confirmation.
        """
        try:
            from app.models.agent_suggestion import AgentSuggestion
            from app.models.driver import Driver

            driver = db.execute(
                select(Driver).where(Driver.id == UUID(driver_id), Driver.tenant_id == tid)
            ).scalar_one_or_none()

            driver_name = driver.full_name if driver else driver_id

            db.add(AgentSuggestion(
                tenant_id=tid,
                plan_date=session.plan_date,
                suggestion_type="FLAG_OVERTIME",
                status="PENDING",
                priority="HIGH",
                title=f"Overtime alert: {driver_name}",
                detail=reason,
                context={"driver_id": driver_id, "session_id": str(session.id)},
            ))
            db.commit()
            return f"Overtime flag created for driver {driver_name}. Dispatcher suggestion is now PENDING review."
        except Exception as exc:
            db.rollback()
            logger.warning("flag_overtime tool error: %s", exc)
            return f"Error flagging overtime: {exc}"

    @tool
    def explain_constraint(constraint_type: str, entity_id: str = "") -> str:
        """
        Generate a plain-language explanation of a planning constraint.
        constraint_type examples: 'time_window', 'vehicle_capacity', 'driver_shift', 'priority_order'.
        entity_id is optional — provide an order_id or driver_id for context-specific explanation.
        """
        if llm is None:
            return "LLM not available — cannot generate explanation."
        try:
            prompt = (
                f"Explain the '{constraint_type}' planning constraint in simple terms a fleet dispatcher would understand. "
                f"{'Entity context: ' + entity_id + '. ' if entity_id else ''}"
                "Keep the explanation under 100 words."
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as exc:
            logger.warning("explain_constraint tool error: %s", exc)
            return f"Error generating explanation: {exc}"

    return [get_current_plan, check_driver_capacity, check_time_window_feasibility,
            move_order, flag_overtime, explain_constraint]


# ─── Main entry point ──────────────────────────────────────────────────────────

def send_planning_message(
    db: Session,
    tenant_id: str,
    planning_session_id: str,
    user_text: str,
) -> tuple[str, bool]:
    """
    Process a dispatcher message in the context of an OPEN planning session.
    Returns (reply_text, used_llm).
    """
    tid = UUID(tenant_id)

    session = db.execute(
        select(PlanningSession).where(
            PlanningSession.id == UUID(planning_session_id),
            PlanningSession.tenant_id == tid,
        )
    ).scalar_one_or_none()

    if not session:
        reply = "Planning session not found."
        _save_messages(db, tid, planning_session_id, user_text, reply)
        return reply, False

    llm = None
    try:
        from app.core.llm_factory import get_llm_for_tenant
        llm = get_llm_for_tenant(db=db, tenant_id=tenant_id)
    except Exception:
        pass

    if llm is None:
        _save_messages(db, tid, planning_session_id, user_text, _FALLBACK_REPLY)
        return _FALLBACK_REPLY, False

    # Build system prompt with planning context
    instructions_block = ""
    try:
        from app.models.planning_instruction import PlanningInstruction
        rules = db.execute(
            select(PlanningInstruction.rule_text)
            .where(PlanningInstruction.tenant_id == tid, PlanningInstruction.is_active.is_(True))
            .order_by(PlanningInstruction.priority, PlanningInstruction.created_at)
            .limit(5)
        ).scalars().all()
        if rules:
            instructions_block = "Active planning rules:\n" + "\n".join(f"  • {r}" for r in rules)
    except Exception:
        pass

    system_content = _SYSTEM_PLANNING.format(
        plan_date=str(session.plan_date),
        plan_id=str(session.active_plan_id) if session.active_plan_id else "none",
        instructions_block=instructions_block,
    )

    # Load tools and bind to LLM
    tools = _make_tools(db, tenant_id, session, llm)
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    # Build message history
    history = _load_history(db, tid, planning_session_id)
    lc_messages: list = [SystemMessage(content=system_content)]
    for msg in history:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    lc_messages.append(HumanMessage(content=user_text))

    # Agentic tool-calling loop
    reply = ""
    for _iteration in range(_MAX_TOOL_ITERATIONS):
        try:
            response: AIMessage = llm_with_tools.invoke(lc_messages)
        except Exception as exc:
            reply = f"Sorry, I encountered an error: {exc}"
            break

        lc_messages.append(response)

        if not response.tool_calls:
            reply = response.content
            break

        # Execute all tool calls in this response
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc.get("id", str(uuid.uuid4()))
            t = tool_map.get(tool_name)
            if t is None:
                tool_result = f"Unknown tool: {tool_name}"
            else:
                try:
                    tool_result = t.invoke(tool_args)
                except Exception as exc:
                    tool_result = f"Tool {tool_name} error: {exc}"
            lc_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

    else:
        # Exhausted iterations — ask LLM for final summary
        try:
            final = llm.invoke(lc_messages + [HumanMessage(content="Please summarise what you've done.")])
            reply = final.content
        except Exception:
            reply = "Action completed. Please review the plan for updated assignments."

    if not reply:
        reply = "I wasn't able to generate a response. Please try again."

    _save_messages(db, tid, planning_session_id, user_text, reply)
    return reply, True
