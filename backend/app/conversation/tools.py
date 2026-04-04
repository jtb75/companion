"""Gemini function-calling tool definitions for D.D."""

_dd_tools = None


def get_dd_tools():
    """Lazily build and return the Tool object."""
    global _dd_tools  # noqa: PLW0603
    if _dd_tools is not None:
        return _dd_tools

    from vertexai.generative_models import (
        FunctionDeclaration,
        Tool,
    )

    list_medications = FunctionDeclaration(
        name="list_medications",
        description=(
            "List the user's active medications "
            "with dosage and frequency."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    list_bills = FunctionDeclaration(
        name="list_bills",
        description=(
            "List the user's bills. "
            "Optionally filter by payment status."
        ),
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": (
                        "Filter by status: "
                        "pending, acknowledged, paid, overdue"
                    ),
                    "enum": [
                        "pending",
                        "acknowledged",
                        "paid",
                        "overdue",
                    ],
                },
            },
        },
    )

    list_appointments = FunctionDeclaration(
        name="list_appointments",
        description=(
            "List the user's upcoming appointments."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    list_todos = FunctionDeclaration(
        name="list_todos",
        description=(
            "List the user's active, incomplete todos."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    get_today_summary = FunctionDeclaration(
        name="get_today_summary",
        description=(
            "Get a priority summary of what needs "
            "attention today: bills, meds, appointments."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    mark_bill_paid = FunctionDeclaration(
        name="mark_bill_paid",
        description="Mark a bill as paid.",
        parameters={
            "type": "object",
            "properties": {
                "bill_id": {
                    "type": "string",
                    "description": "UUID of the bill.",
                },
            },
            "required": ["bill_id"],
        },
    )

    confirm_medication_taken = FunctionDeclaration(
        name="confirm_medication_taken",
        description=(
            "Record that the user took a medication dose."
        ),
        parameters={
            "type": "object",
            "properties": {
                "medication_id": {
                    "type": "string",
                    "description": (
                        "UUID of the medication."
                    ),
                },
            },
            "required": ["medication_id"],
        },
    )

    add_appointment = FunctionDeclaration(
        name="add_appointment",
        description="Add a new appointment.",
        parameters={
            "type": "object",
            "properties": {
                "provider_name": {
                    "type": "string",
                    "description": (
                        "Name of the provider or office."
                    ),
                },
                "appointment_at": {
                    "type": "string",
                    "description": (
                        "ISO-8601 datetime for the "
                        "appointment."
                    ),
                },
                "preparation_notes": {
                    "type": "string",
                    "description": (
                        "Optional notes on how to prepare."
                    ),
                },
                "review_id": {
                    "type": "string",
                    "description": (
                        "Optional ID of the document review "
                        "this appointment is related to."
                    ),
                },
            },
            "required": [
                "provider_name",
                "appointment_at",
            ],
        },
    )

    add_todo = FunctionDeclaration(
        name="add_todo",
        description="Add a new todo item.",
        parameters={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": (
                        "Short description of the task."
                    ),
                },
                "due_date": {
                    "type": "string",
                    "description": (
                        "Optional due date in YYYY-MM-DD."
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Optional category for the todo."
                    ),
                    "enum": [
                        "errand",
                        "shopping",
                        "task",
                        "general",
                    ],
                },
                "review_id": {
                    "type": "string",
                    "description": (
                        "Optional ID of the document review "
                        "this todo is related to."
                    ),
                },
            },
            "required": ["title"],
        },
    )

    complete_todo = FunctionDeclaration(
        name="complete_todo",
        description="Mark a todo as completed.",
        parameters={
            "type": "object",
            "properties": {
                "todo_id": {
                    "type": "string",
                    "description": "UUID of the todo.",
                },
            },
            "required": ["todo_id"],
        },
    )

    get_pending_reviews = FunctionDeclaration(
        name="get_pending_reviews",
        description=(
            "List documents waiting for the user to "
            "review. Returns pending document reviews "
            "with summaries and recommended actions."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    )

    confirm_document_action = FunctionDeclaration(
        name="confirm_document_action",
        description=(
            "Confirm or skip a pending document review. "
            "Use 'confirm' to create the recommended "
            "record, 'skip' to dismiss, or 'mark_paid' "
            "for bills the user already paid."
        ),
        parameters={
            "type": "object",
            "properties": {
                "review_id": {
                    "type": "string",
                    "description": (
                        "UUID of the pending review."
                    ),
                },
                "action": {
                    "type": "string",
                    "description": (
                        "Action to take on the review."
                    ),
                    "enum": [
                        "confirm",
                        "skip",
                        "mark_paid",
                    ],
                },
            },
            "required": ["review_id", "action"],
        },
    )

    update_review_fields = FunctionDeclaration(
        name="update_review_fields",
        description=(
            "Correct extracted fields on a pending "
            "review before confirming. Use when the "
            "user says the amount or date is wrong."
        ),
        parameters={
            "type": "object",
            "properties": {
                "review_id": {
                    "type": "string",
                    "description": (
                        "UUID of the pending review."
                    ),
                },
                "field_updates": {
                    "type": "object",
                    "description": (
                        "Fields to update, e.g. "
                        '{"amount_due": "142.50"}'
                    ),
                },
            },
            "required": ["review_id", "field_updates"],
        },
    )

    _dd_tools = Tool(
        function_declarations=[
            list_medications,
            list_bills,
            list_appointments,
            list_todos,
            get_today_summary,
            mark_bill_paid,
            confirm_medication_taken,
            add_appointment,
            add_todo,
            complete_todo,
            get_pending_reviews,
            confirm_document_action,
            update_review_fields,
        ],
    )
    return _dd_tools
