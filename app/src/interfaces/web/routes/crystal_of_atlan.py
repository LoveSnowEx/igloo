"""Crystal of Atlan enhancement calculator — page routes."""

import json

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from ....modules.crystal_of_atlan.schemas import (
    CATALYST_LABELS,
    CalculateRequest,
    CatalystType,
    EnhanceResult,
    EnhanceState,
)
from ....modules.crystal_of_atlan.service import apply_result, calculate
from ..deps import templates

router = APIRouter()

MAX_IMPORT_BYTES = 1_048_576
CATALYST_OPTIONS = [(ct.value, CATALYST_LABELS[ct]) for ct in CatalystType]


@router.get("/crystal-of-atlan/enhance", response_class=HTMLResponse)
async def page(request: Request) -> HTMLResponse:
    """Render the enhancement calculator page."""
    state = EnhanceState(current_level=10, progress={})
    return _render_page(request, state)


@router.post("/crystal-of-atlan/enhance")
async def page_action(request: Request):
    """Handle page actions (calculate, record, import/export)."""
    form = await request.form()
    action = str(form.get("action", "calculate"))

    state = _state_from_form(form)

    parse_errors: list[str] = []
    for i in range(15):
        key = f"progress_{i}"
        if key in form:
            try:
                state.progress[i] = int(str(form[key]))
            except (ValueError, TypeError):
                parse_errors.append(f"+{i} progress format invalid")

    selected_catalyst = str(form.get("catalyst", "none"))
    flash_message = ""
    flash_type = ""
    result: dict | None = None

    if parse_errors:
        flash_message = "⚠️ " + "; ".join(parse_errors)
        flash_type = "failure"
        return _render_page(
            request, state, selected_catalyst,
            result, flash_message, flash_type,
        )

    if action == "calculate":
        progress_val = state.progress.get(state.current_level, 0)
        calc_request = CalculateRequest(
            current_level=state.current_level,
            progress=progress_val,
            catalyst=CatalystType(selected_catalyst),
        )
        result = calculate(calc_request).model_dump()
        state.progress[state.current_level] = progress_val

    elif action == "record_success":
        catalyst = CatalystType(selected_catalyst)
        state = apply_result(state, EnhanceResult.SUCCESS, catalyst)
        flash_message = f"🎉 Enhancement success! Current level: +{state.current_level}"
        flash_type = "success"

    elif action == "record_failure":
        catalyst = CatalystType(selected_catalyst)
        old_level = state.current_level
        state = apply_result(state, EnhanceResult.FAILURE, catalyst)
        msg = f"💔 Enhancement failed! +{state.current_level} progress +1"
        if state.current_level < old_level:
            msg += f", level dropped: +{old_level} → +{state.current_level}"
        flash_message = msg
        flash_type = "failure"

    elif action == "export":
        return JSONResponse(
            content=state.model_dump(),
            headers={
                "Content-Disposition": (
                    "attachment; filename=crystal-of-atlan-enhance-state.json"
                ),
            },
        )

    elif action == "import":
        import_file = form.get("import_file")
        if isinstance(import_file, UploadFile):
            try:
                content = await import_file.read(size=MAX_IMPORT_BYTES)
                data = json.loads(content)
                state = EnhanceState.model_validate(data)
                flash_message = (
                    f"📤 Imported! Current level: +{state.current_level}"
                )
                flash_type = "success"
            except (json.JSONDecodeError, ValueError):
                flash_message = "⚠️ Invalid JSON format or data structure"
                flash_type = "failure"
        else:
            flash_message = "⚠️ Please select a JSON file to import"
            flash_type = "failure"

    return _render_page(
        request, state, selected_catalyst,
        result, flash_message, flash_type,
    )


def _state_from_form(form) -> EnhanceState:
    """Rebuild EnhanceState from form data."""
    state_json = form.get("state_json", "{}")
    raw = state_json if isinstance(state_json, str) else str(state_json)
    return EnhanceState.model_validate_json(raw)


def _render_page(
    request: Request,
    state: EnhanceState,
    selected_catalyst: str = "none",
    result: dict | None = None,
    flash_message: str = "",
    flash_type: str = "",
) -> HTMLResponse:
    """Render the Jinja2 page template."""
    progress = {str(k): v for k, v in state.progress.items()}
    state_json = state.model_dump_json()

    return templates.TemplateResponse(
        request=request,
        name="pages/crystal_of_atlan.html",
        context={
            "current_level": state.current_level,
            "progress": progress,
            "state_json": state_json,
            "selected_catalyst": selected_catalyst,
            "catalyst_options": CATALYST_OPTIONS,
            "result": result,
            "flash_message": flash_message,
            "flash_type": flash_type,
        },
    )
