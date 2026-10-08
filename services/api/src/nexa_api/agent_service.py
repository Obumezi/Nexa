from difflib import SequenceMatcher
from inspect import signature

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nexa_api.conversation_context import (
    build_skill_context,
    format_skill_context,
)
from nexa_api.delivery_service import (
    list_deliveries,
    mark_delivery_collected,
    mark_delivery_delivered,
)
from nexa_api.enums import (
    DeliveryStatus,
    PresenceStatus,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.llm_service import resolve_intent_with_llm
from nexa_api.models import (
    Delivery,
    ExpectedVisitor,
    HouseholdPresence,
    HouseholdTask,
)
from nexa_api.presence_service import (
    list_presence,
    update_presence,
)
from nexa_api.schemas import (
    AgentDecision,
    AgentIntent,
    AgentResponse,
    PresenceUpdate,
    TaskCreate,
)
from nexa_api.task_service import (
    complete_task,
    create_task,
    list_tasks,
)
from nexa_api.visitor_service import (
    cancel_visitor,
    list_visitors,
    mark_visitor_arrived,
    mark_visitor_departed,
)


def resolve_intent(message: str) -> AgentDecision:
    """Resolve common natural-language requests locally."""

    normalized = message.lower().strip()

    if any(
        phrase in normalized
        for phrase in (
            "expected visitor",
            "expected today",
            "who is coming",
            "who is visiting",
            "visitors today",
        )
    ):
        return AgentDecision(
            intent=AgentIntent.GET_EXPECTED_VISITORS,
            confidence=1.0,
        )

    if any(
        phrase in normalized
        for phrase in (
            "pending delivery",
            "expected delivery",
            "packages coming",
            "package coming",
            "deliveries coming",
        )
    ):
        return AgentDecision(
            intent=AgentIntent.GET_PENDING_DELIVERIES,
            confidence=1.0,
        )

    if any(
        phrase in normalized
        for phrase in (
            "who is home",
            "who's home",
            "household presence",
            "who is away",
            "who's away",
        )
    ):
        return AgentDecision(
            intent=AgentIntent.GET_HOUSEHOLD_PRESENCE,
            confidence=1.0,
        )

    if any(
        phrase in normalized
        for phrase in (
            "open tasks",
            "pending tasks",
            "what needs to be done",
            "things to do",
        )
    ):
        return AgentDecision(
            intent=AgentIntent.GET_OPEN_TASKS,
            confidence=1.0,
        )

    return AgentDecision(
        intent=AgentIntent.UNKNOWN,
        confidence=0.0,
    )

def _resolve_with_llm(
    message: str,
    history: list[dict[str, str]] | None = None,
    speaker_name: str | None = None,
) -> AgentDecision:
    """Call the LLM resolver with supported conversational context."""

    skill_context = format_skill_context(
        build_skill_context(message)
    )

    resolver_parameters = signature(
        resolve_intent_with_llm
    ).parameters

    kwargs: dict[str, object] = {}

    if history and "history" in resolver_parameters:
        kwargs["history"] = history

    if speaker_name and "speaker_name" in resolver_parameters:
        kwargs["speaker_name"] = speaker_name

    if skill_context and "skill_context" in resolver_parameters:
        kwargs["skill_context"] = skill_context

    return resolve_intent_with_llm(
        message,
        **kwargs,
    )


def resolve_agent_intent(
    message: str,
    history: list[dict[str, str]] | None = None,
    speaker_name: str | None = None,
) -> AgentDecision:
    """Resolve an agent intent using deterministic and LLM routing."""

    decision = resolve_intent(message)

    if decision.intent != AgentIntent.UNKNOWN:
        return decision

    return _resolve_with_llm(
        message,
        history=history,
        speaker_name=speaker_name,
    )

def find_open_task_by_title(
    session: Session,
    title: str,
) -> HouseholdTask | None:
    """Find an open task using a case-insensitive exact title."""

    normalized_title = title.strip().lower()

    statement = (
        select(HouseholdTask)
        .where(
            HouseholdTask.status == TaskStatus.OPEN,
            func.lower(HouseholdTask.title) == normalized_title,
        )
        .order_by(HouseholdTask.created_at.desc())
    )

    return session.scalar(statement)

def find_open_task_fuzzy(
    session: Session,
    title: str,
    threshold: float = 0.65,
) -> HouseholdTask | None:
    """Find one open task by a safe fuzzy title match."""

    normalized_target = title.strip().casefold()

    if not normalized_target:
        return None

    tasks = list(
        session.scalars(
            select(HouseholdTask).where(
                HouseholdTask.status == TaskStatus.OPEN,
            )
        )
    )

    matches: list[tuple[float, HouseholdTask]] = []

    for task in tasks:
        normalized_title = task.title.strip().casefold()

        if normalized_target in normalized_title:
            score = 1.0
        else:
            score = SequenceMatcher(
                None,
                normalized_target,
                normalized_title,
            ).ratio()

        if score >= threshold:
            matches.append(
                (
                    score,
                    task,
                )
            )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score = matches[0][0]

    best_matches = [
        task
        for score, task in matches
        if score == best_score
    ]

    if len(best_matches) != 1:
        return None

    return best_matches[0]

def find_expected_visitor_by_name(
    session: Session,
    name: str,
) -> ExpectedVisitor | None:
    """Find an expected visitor using a case-insensitive exact name."""

    normalized_name = name.strip().lower()

    statement = (
        select(ExpectedVisitor)
        .where(
            ExpectedVisitor.status == VisitorStatus.EXPECTED,
            func.lower(ExpectedVisitor.name) == normalized_name,
        )
        .order_by(ExpectedVisitor.created_at.desc())
    )

    return session.scalar(statement)

def find_expected_visitor_fuzzy(
    session: Session,
    name: str,
    threshold: float = 0.65,
) -> ExpectedVisitor | None:
    """Find one expected visitor by a safe fuzzy name match."""

    normalized_target = name.strip().casefold()

    if not normalized_target:
        return None

    visitors = list(
        session.scalars(
            select(ExpectedVisitor).where(
                ExpectedVisitor.status == VisitorStatus.EXPECTED,
            )
        )
    )

    matches: list[tuple[float, ExpectedVisitor]] = []

    for visitor in visitors:
        normalized_name = visitor.name.strip().casefold()

        if normalized_target in normalized_name:
            score = 1.0
        else:
            score = SequenceMatcher(
                None,
                normalized_target,
                normalized_name,
            ).ratio()

        if score >= threshold:
            matches.append(
                (
                    score,
                    visitor,
                )
            )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score = matches[0][0]

    best_matches = [
        visitor
        for score, visitor in matches
        if score == best_score
    ]

    if len(best_matches) != 1:
        return None

    return best_matches[0]

def find_arrived_visitor_by_name(
    session: Session,
    name: str,
) -> ExpectedVisitor | None:
    """Find an arrived visitor using a case-insensitive exact name."""

    normalized_name = name.strip().lower()

    statement = (
        select(ExpectedVisitor)
        .where(
            ExpectedVisitor.status == VisitorStatus.ARRIVED,
            func.lower(ExpectedVisitor.name) == normalized_name,
        )
        .order_by(ExpectedVisitor.arrived_at.desc())
    )

    return session.scalar(statement)

def find_arrived_visitor_fuzzy(
    session: Session,
    name: str,
    threshold: float = 0.65,
) -> ExpectedVisitor | None:
    """Find one arrived visitor by a safe fuzzy name match."""

    normalized_target = name.strip().casefold()

    if not normalized_target:
        return None

    visitors = list(
        session.scalars(
            select(ExpectedVisitor).where(
                ExpectedVisitor.status == VisitorStatus.ARRIVED,
            )
        )
    )

    matches: list[tuple[float, ExpectedVisitor]] = []

    for visitor in visitors:
        normalized_name = visitor.name.strip().casefold()

        if normalized_target in normalized_name:
            score = 1.0
        else:
            score = SequenceMatcher(
                None,
                normalized_target,
                normalized_name,
            ).ratio()

        if score >= threshold:
            matches.append(
                (
                    score,
                    visitor,
                )
            )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score = matches[0][0]

    best_matches = [
        visitor
        for score, visitor in matches
        if score == best_score
    ]

    if len(best_matches) != 1:
        return None

    return best_matches[0]

def find_presence_by_occupant_name(
    session: Session,
    occupant_name: str,
) -> HouseholdPresence | None:
    """Find a household presence record by occupant name."""

    normalized_name = occupant_name.strip().lower()

    statement = (
        select(HouseholdPresence)
        .where(func.lower(HouseholdPresence.occupant_name) == normalized_name)
        .order_by(HouseholdPresence.since.desc())
    )

    return session.scalar(statement)


def find_delivered_delivery(
    session: Session,
    description: str,
) -> Delivery | None:
    """Find a delivered package using a case-insensitive identifier."""

    normalized_description = description.strip().lower()

    statement = (
        select(Delivery)
        .where(
            Delivery.status == DeliveryStatus.DELIVERED,
            func.lower(Delivery.description) == normalized_description,
        )
        .order_by(Delivery.delivered_at.desc())
    )

    return session.scalar(statement)

def find_delivered_delivery_fuzzy(
    session: Session,
    description: str,
    threshold: float = 0.65,
) -> Delivery | None:
    """Find one delivered package by a safe fuzzy description match."""

    normalized_target = description.strip().casefold()

    if not normalized_target:
        return None

    deliveries = list(
        session.scalars(
            select(Delivery).where(
                Delivery.status == DeliveryStatus.DELIVERED,
            )
        )
    )

    matches: list[tuple[float, Delivery]] = []

    for delivery in deliveries:
        normalized_description = delivery.description.strip().casefold()

        if normalized_target in normalized_description:
            score = 1.0
        else:
            score = SequenceMatcher(
                None,
                normalized_target,
                normalized_description,
            ).ratio()

        if score >= threshold:
            matches.append(
                (
                    score,
                    delivery,
                )
            )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score = matches[0][0]

    best_matches = [
        delivery
        for score, delivery in matches
        if score == best_score
    ]

    if len(best_matches) != 1:
        return None

    return best_matches[0]

def run_agent(
    session: Session,
    message: str,
    confirm: bool = False,
    history: list[dict[str, str]] | None = None,
    speaker_name: str | None = None,
) -> AgentResponse:
    """Process a supported Nexa natural-language request."""

    if history and speaker_name:
        decision = resolve_agent_intent(
            message,
            history=history,
            speaker_name=speaker_name,
        )
    elif history:
        decision = resolve_agent_intent(
            message,
            history=history,
        )
    elif speaker_name:
        decision = resolve_agent_intent(
            message,
            speaker_name=speaker_name,
        )
    else:
        decision = resolve_agent_intent(message)

    # ---------------------------------------------------------
    # CREATE TASK
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.CREATE_TASK:
        if not decision.task_title:
            return AgentResponse(  # noqa: F706
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to create a task, "
                    "but I could not determine the task title."
                ),
            )

        proposed_action: dict[str, object] = {
            "title": decision.task_title,
        }

        if decision.task_description:
            proposed_action["description"] = decision.task_description

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.CREATE_TASK,
                message=(f"Create the task '{decision.task_title}'?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        task = create_task(
            session,
            TaskCreate(
                title=decision.task_title,
                description=decision.task_description,
            ),
        )

        return AgentResponse(
            intent=AgentIntent.CREATE_TASK,
            message=f"Task created: {task.title}.",
            data=[
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # COMPLETE TASK
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.COMPLETE_TASK:
        if not decision.target_task_title:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to complete a task, "
                    "but I could not determine which task."
                ),
            )

        task_title = decision.target_task_title

        task = find_open_task_by_title(
            session,
            task_title,
        )

        if task is None:
            task = find_open_task_fuzzy(
                session,
                task_title,
            )

        if task is None:
            return AgentResponse(
                intent=AgentIntent.COMPLETE_TASK,
                message=(
                    "I could not find a unique open task matching "
                    f"'{task_title}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "task_id": task.id,
            "title": task.title,
            "action": "complete",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.COMPLETE_TASK,
                message=(f"Mark the task '{task.title}' as completed?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        completed_task = complete_task(
            session,
            task,
        )

        return AgentResponse(
            intent=AgentIntent.COMPLETE_TASK,
            message=(f"Task completed: {completed_task.title}."),
            data=[
                {
                    "id": completed_task.id,
                    "title": completed_task.title,
                    "status": completed_task.status,
                    "completed_at": (completed_task.completed_at),
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # CANCEL VISITOR
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.CANCEL_VISITOR:
        if not decision.target_visitor_name:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to cancel a visitor, "
                    "but I could not determine which visitor."
                ),
            )

        visitor = find_expected_visitor_by_name(
            session,
            decision.target_visitor_name,
        )

        if visitor is None:
            visitor = find_expected_visitor_fuzzy(
                session,
                decision.target_visitor_name,
            )

        if visitor is None:
            return AgentResponse(
                intent=AgentIntent.CANCEL_VISITOR,
                message=(
                    "I could not find a unique expected visitor matching "
                    f"'{decision.target_visitor_name}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "visitor_id": visitor.id,
            "name": visitor.name,
            "action": "cancel",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.CANCEL_VISITOR,
                message=(f"Cancel the expected visit from '{visitor.name}'?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        cancelled_visitor = cancel_visitor(
            session,
            visitor,
        )

        return AgentResponse(
            intent=AgentIntent.CANCEL_VISITOR,
            message=(f"Visit cancelled: {cancelled_visitor.name}."),
            data=[
                {
                    "id": cancelled_visitor.id,
                    "name": cancelled_visitor.name,
                    "status": cancelled_visitor.status,
                    "expected_start": (cancelled_visitor.expected_start),
                    "expected_end": (cancelled_visitor.expected_end),
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # MARK VISITOR ARRIVED
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.MARK_VISITOR_ARRIVED:
        if not decision.target_visitor_name:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that a visitor has arrived, "
                    "but I could not determine which visitor."
                ),
            )

        target_visitor_name = decision.target_visitor_name

        visitor = find_expected_visitor_by_name(
            session,
            target_visitor_name,
        )

        if visitor is None:
            visitor = find_expected_visitor_fuzzy(
                session,
                target_visitor_name,
            )

        if visitor is None:
            return AgentResponse(
                intent=AgentIntent.MARK_VISITOR_ARRIVED,
                message=(
                    "I could not find a unique expected visitor matching "
                    f"'{target_visitor_name}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "visitor_id": visitor.id,
            "name": visitor.name,
            "action": "mark_arrived",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.MARK_VISITOR_ARRIVED,
                message=(f"Mark '{visitor.name}' as arrived?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        arrived_visitor = mark_visitor_arrived(
            session,
            visitor,
        )

        return AgentResponse(
            intent=AgentIntent.MARK_VISITOR_ARRIVED,
            message=(f"Visitor marked as arrived: {arrived_visitor.name}."),
            data=[
                {
                    "id": arrived_visitor.id,
                    "name": arrived_visitor.name,
                    "status": arrived_visitor.status,
                    "arrived_at": arrived_visitor.arrived_at,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # MARK VISITOR DEPARTED
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.MARK_VISITOR_DEPARTED:
        if not decision.target_visitor_name:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that a visitor has left, but I could not determine which visitor."
                ),
            )

        target_visitor_name = decision.target_visitor_name

        visitor = find_arrived_visitor_by_name(
            session,
            target_visitor_name,
        )

        if visitor is None:
            visitor = find_arrived_visitor_fuzzy(
                session,
                target_visitor_name,
            )

        if visitor is None:
            return AgentResponse(
                intent=AgentIntent.MARK_VISITOR_DEPARTED,
                message=(
                    "I could not find a unique arrived visitor matching "
                    f"'{target_visitor_name}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "visitor_id": visitor.id,
            "name": visitor.name,
            "action": "mark_departed",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.MARK_VISITOR_DEPARTED,
                message=(f"Mark '{visitor.name}' as departed?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        departed_visitor = mark_visitor_departed(
            session,
            visitor,
        )

        return AgentResponse(
            intent=AgentIntent.MARK_VISITOR_DEPARTED,
            message=(f"Visitor marked as departed: {departed_visitor.name}."),
            data=[
                {
                    "id": departed_visitor.id,
                    "name": departed_visitor.name,
                    "status": departed_visitor.status,
                    "arrived_at": departed_visitor.arrived_at,
                    "departed_at": departed_visitor.departed_at,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # EXPECTED VISITORS
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.GET_EXPECTED_VISITORS:
        visitors = list_visitors(
            session,
            status=VisitorStatus.EXPECTED,
        )

        data = [
            {
                "id": visitor.id,
                "name": visitor.name,
                "purpose": visitor.purpose,
                "expected_start": visitor.expected_start,
                "expected_end": visitor.expected_end,
            }
            for visitor in visitors
        ]

        if not visitors:
            message_text = "No visitors are currently expected."
        elif len(visitors) == 1:
            message_text = f"{visitors[0].name} is currently expected."
        else:
            message_text = f"{len(visitors)} visitors are currently expected."

        return AgentResponse(
            intent=decision.intent,
            message=message_text,
            data=data,
        )

    # ---------------------------------------------------------
    # MARK DELIVERY DELIVERED
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.MARK_DELIVERY_DELIVERED:
        if not decision.target_delivery_description:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to mark a delivery as delivered, "
                    "but I could not determine which delivery."
                ),
            )

        delivery = find_expected_delivery(
            session,
            decision.target_delivery_description,
        )

        if delivery is None:
            delivery = find_expected_delivery_fuzzy(
                session,
                decision.target_delivery_description,
            )

        if delivery is None:
            return AgentResponse(
                intent=AgentIntent.MARK_DELIVERY_DELIVERED,
                message=(
                    "I could not find a unique expected delivery matching "
                    f"'{decision.target_delivery_description}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "delivery_id": delivery.id,
            "description": delivery.description,
            "action": "mark_delivered",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.MARK_DELIVERY_DELIVERED,
                message=(f"Mark '{delivery.description}' as delivered?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        delivered_delivery = mark_delivery_delivered(
            session,
            delivery,
        )

        return AgentResponse(
            intent=AgentIntent.MARK_DELIVERY_DELIVERED,
            message=(f"Delivery marked as delivered: {delivered_delivery.description}."),
            data=[
                {
                    "id": delivered_delivery.id,
                    "description": delivered_delivery.description,
                    "carrier": delivered_delivery.carrier,
                    "tracking_reference": (delivered_delivery.tracking_reference),
                    "status": delivered_delivery.status,
                    "delivered_at": delivered_delivery.delivered_at,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # MARK DELIVERY COLLECTED
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.MARK_DELIVERY_COLLECTED:
        target_delivery_description = decision.target_delivery_description
        if not target_delivery_description:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to collect a delivery, "
                    "but I could not determine which delivery."
                ),
            )

        delivery = find_delivered_delivery(
            session,
            target_delivery_description,
        )

        if delivery is None:
            delivery = find_delivered_delivery_fuzzy(
                session,
                target_delivery_description,
            )

        if delivery is None:
            return AgentResponse(
                intent=AgentIntent.MARK_DELIVERY_COLLECTED,
                message=(
                    "I could not find a unique delivered package matching "
                    f"'{target_delivery_description}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "delivery_id": delivery.id,
            "description": delivery.description,
            "action": "mark_collected",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.MARK_DELIVERY_COLLECTED,
                message=(f"Mark '{delivery.description}' as collected?"),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        collected_delivery = mark_delivery_collected(
            session,
            delivery,
        )

        return AgentResponse(
            intent=AgentIntent.MARK_DELIVERY_COLLECTED,
            message=(f"Delivery marked as collected: {collected_delivery.description}."),
            data=[
                {
                    "id": collected_delivery.id,
                    "description": collected_delivery.description,
                    "carrier": collected_delivery.carrier,
                    "tracking_reference": (collected_delivery.tracking_reference),
                    "status": collected_delivery.status,
                    "delivered_at": collected_delivery.delivered_at,
                    "collected_at": collected_delivery.collected_at,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # DELIVERIES
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.GET_PENDING_DELIVERIES:
        deliveries = list_deliveries(
            session,
            status=DeliveryStatus.EXPECTED,
        )

        data = [
            {
                "id": delivery.id,
                "description": delivery.description,
                "carrier": delivery.carrier,
                "tracking_reference": (delivery.tracking_reference),
                "expected_at": delivery.expected_at,
            }
            for delivery in deliveries
        ]

        if not deliveries:
            message_text = "No deliveries are currently expected."
        elif len(deliveries) == 1:
            message_text = f"One delivery is currently expected: {deliveries[0].description}."
        else:
            message_text = f"{len(deliveries)} deliveries are currently expected."

        return AgentResponse(
            intent=decision.intent,
            message=message_text,
            data=data,
        )

    # ---------------------------------------------------------
    # UPDATE PRESENCE
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.UPDATE_PRESENCE:
        if not decision.target_occupant_name:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to update household "
                    "presence, but I could not determine which person."
                ),
            )

        if not decision.target_presence_status:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=(
                    "I understood that you want to update household "
                    "presence, but I could not determine the new status."
                ),
            )

        try:
            new_status = PresenceStatus(decision.target_presence_status.lower())
        except ValueError:
            return AgentResponse(
                intent=AgentIntent.UNKNOWN,
                message=("I could not determine a valid household presence status."),
            )

        presence = find_presence_by_occupant_name(
            session,
            decision.target_occupant_name,
        )

        if presence is None:
            return AgentResponse(
                intent=AgentIntent.UPDATE_PRESENCE,
                message=(
                    f"I could not find a household member named '{decision.target_occupant_name}'."
                ),
                action_executed=False,
            )

        proposed_action: dict[str, object] = {
            "presence_id": presence.id,
            "occupant_name": presence.occupant_name,
            "current_status": presence.status,
            "new_status": new_status,
            "action": "update_presence",
        }

        if not confirm:
            return AgentResponse(
                intent=AgentIntent.UPDATE_PRESENCE,
                message=(
                    f"Change {presence.occupant_name}'s status "
                    f"from '{presence.status}' to '{new_status}'?"
                ),
                requires_confirmation=True,
                action_executed=False,
                proposed_action=proposed_action,
            )

        updated_presence = update_presence(
            session,
            presence,
            PresenceUpdate(
                status=new_status,
            ),
        )

        return AgentResponse(
            intent=AgentIntent.UPDATE_PRESENCE,
            message=(
                f"Presence updated: "
                f"{updated_presence.occupant_name} is now "
                f"{updated_presence.status}."
            ),
            data=[
                {
                    "id": updated_presence.id,
                    "occupant_name": (updated_presence.occupant_name),
                    "status": updated_presence.status,
                    "since": updated_presence.since,
                    "note": updated_presence.note,
                }
            ],
            requires_confirmation=False,
            action_executed=True,
        )

    # ---------------------------------------------------------
    # HOUSEHOLD PRESENCE
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.GET_HOUSEHOLD_PRESENCE:
        presence = list_presence(session)

        data = [
            {
                "id": record.id,
                "occupant_name": record.occupant_name,
                "status": record.status,
                "since": record.since,
            }
            for record in presence
        ]

        if not presence:
            message_text = "No household presence records are available."
        else:
            message_text = f"I found {len(presence)} household presence records."

        return AgentResponse(
            intent=decision.intent,
            message=message_text,
            data=data,
        )

    # ---------------------------------------------------------
    # OPEN TASKS
    # ---------------------------------------------------------

    if decision.intent == AgentIntent.GET_OPEN_TASKS:
        tasks = list_tasks(
            session,
            status=TaskStatus.OPEN,
        )

        data = [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "due_at": task.due_at,
                "requires_confirmation": (task.requires_confirmation),
            }
            for task in tasks
        ]

        if not tasks:
            message_text = "There are no open household tasks."
        elif len(tasks) == 1:
            message_text = f"You have one open task: {tasks[0].title}."
        else:
            message_text = f"You have {len(tasks)} open household tasks."

        return AgentResponse(
            intent=decision.intent,
            message=message_text,
            data=data,
        )

    return AgentResponse(
        intent=AgentIntent.UNKNOWN,
        message=("I don't know how to handle that request yet."),
    )


def find_expected_delivery(
    session: Session,
    description: str,
) -> Delivery | None:
    """Find an expected delivery using a case-insensitive identifier."""

    normalized_description = description.strip().lower()

    statement = (
        select(Delivery)
        .where(
            Delivery.status == DeliveryStatus.EXPECTED,
            func.lower(Delivery.description) == normalized_description,
        )
        .order_by(Delivery.created_at.desc())
    )

    return session.scalar(statement)

def find_expected_delivery_fuzzy(
    session: Session,
    description: str,
    threshold: float = 0.65,
) -> Delivery | None:
    """Find one expected delivery by a safe fuzzy description match."""

    normalized_target = description.strip().casefold()

    if not normalized_target:
        return None

    deliveries = list(
        session.scalars(
            select(Delivery).where(
                Delivery.status == DeliveryStatus.EXPECTED,
            )
        )
    )

    matches: list[tuple[float, Delivery]] = []

    for delivery in deliveries:
        normalized_description = delivery.description.strip().casefold()

        if normalized_target in normalized_description:
            score = 1.0
        else:
            score = SequenceMatcher(
                None,
                normalized_target,
                normalized_description,
            ).ratio()

        if score >= threshold:
            matches.append(
                (
                    score,
                    delivery,
                )
            )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score = matches[0][0]
    best_matches = [
        delivery
        for score, delivery in matches
        if score == best_score
    ]

    if len(best_matches) != 1:
        return None

    return best_matches[0]
