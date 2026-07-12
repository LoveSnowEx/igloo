"""Crystal of Atlan 裝備強化計算器 — API 端點。"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.datastructures import FormData

from app.core.templates import templates
from app.schemas.crystal_of_atlan.enhance import (
    CATALYST_LABELS,
    CalculateRequest,
    CalculateResponse,
    CatalystType,
    EnhanceResult,
    EnhanceState,
    ImportResponse,
    RecordResultRequest,
)
from app.services.crystal_of_atlan.enhance import apply_result, calculate

router = APIRouter(prefix="/api/crystal-of-atlan", tags=["Crystal of Atlan"])


@router.post("/calculate", response_model=CalculateResponse)
async def calculate_endpoint(request: CalculateRequest) -> CalculateResponse:
    """計算強化策略。"""
    return calculate(request)


@router.post("/record", response_model=EnhanceState)
async def record_endpoint(request: RecordResultRequest) -> EnhanceState:
    """記錄強化結果並更新狀態。"""
    return apply_result(request.state, request.result, request.catalyst)


@router.post("/export")
async def export_endpoint(state: EnhanceState) -> JSONResponse:
    """匯出強化狀態為 JSON 下載。"""
    return _export_response(state)


@router.post("/import", response_model=ImportResponse)
async def import_endpoint(file: UploadFile) -> ImportResponse:
    """匯入強化狀態 JSON 檔案。"""
    content = await file.read(size=1_048_576)
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid JSON format",
        ) from None
    try:
        state = EnhanceState.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=422, detail="Invalid enhancement state data",
        ) from None
    return ImportResponse(
        state=state,
        message=f"成功匯入強化狀態（目前等級：+{state.current_level}）",
    )


# === 頁面端點 ===

page_router = APIRouter(tags=["Crystal of Atlan Page"])

MAX_IMPORT_BYTES = 1_048_576
CATALYST_OPTIONS = [(ct.value, CATALYST_LABELS[ct]) for ct in CatalystType]


def _export_response(state: EnhanceState) -> JSONResponse:
    """產生匯出 JSON 下載回應。"""
    return JSONResponse(
        content=state.model_dump(),
        headers={
            "Content-Disposition": (
                "attachment; filename=crystal-of-atlan-enhance-state.json"
            ),
        },
    )


def _state_from_form(form: FormData) -> EnhanceState:
    """從表單資料重建 EnhanceState。"""
    state_json = form.get("state_json", "{}")
    raw = state_json if isinstance(state_json, str) else str(state_json)
    return EnhanceState.model_validate_json(raw)


@page_router.get("/crystal-of-atlan", response_class=HTMLResponse)
async def page(request: Request) -> HTMLResponse:
    """渲染強化計算器頁面。"""
    state = EnhanceState(current_level=10, progress={})
    return _render_page(request, state)


@page_router.post("/crystal-of-atlan")
async def page_action(request: Request) -> Response:
    """處理頁面操作（計算、記錄結果、匯入/匯出）。"""
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
                parse_errors.append(f"+{i} 進度格式無效")

    selected_catalyst = str(form.get("catalyst", "none"))
    flash_message = ""
    flash_type = ""
    result: dict[str, Any] | None = None

    if parse_errors:
        flash_message = "⚠️ " + "；".join(parse_errors)
        flash_type = "failure"
        return _render_page(
            request, state, selected_catalyst,
            result, flash_message, flash_type,
        )

    if action == "calculate":
        progress = state.progress.get(state.current_level, 0)
        calc_request = CalculateRequest(
            current_level=state.current_level,
            progress=progress,
            catalyst=CatalystType(selected_catalyst),
        )
        result = calculate(calc_request).model_dump()
        state.progress[state.current_level] = progress

    elif action == "record_success":
        catalyst = CatalystType(selected_catalyst)
        state = apply_result(state, EnhanceResult.SUCCESS, catalyst)
        flash_message = f"🎉 強化成功！目前等級：+{state.current_level}"
        flash_type = "success"

    elif action == "record_failure":
        catalyst = CatalystType(selected_catalyst)
        old_level = state.current_level
        state = apply_result(state, EnhanceResult.FAILURE, catalyst)
        msg = f"💔 強化失敗！+{state.current_level} 進度 +1"
        if state.current_level < old_level:
            msg += f"，降等：+{old_level} → +{state.current_level}"
        flash_message = msg
        flash_type = "failure"

    elif action == "export":
        return _export_response(state)

    elif action == "import":
        import_file = form.get("import_file")
        if isinstance(import_file, UploadFile):
            try:
                content = await import_file.read(size=MAX_IMPORT_BYTES)
                data = json.loads(content)
                state = EnhanceState.model_validate(data)
                flash_message = (
                    f"📤 成功匯入！目前等級：+{state.current_level}"
                )
                flash_type = "success"
            except (json.JSONDecodeError, ValueError):
                flash_message = "⚠️ JSON 格式無效或資料結構不符"
                flash_type = "failure"
        else:
            flash_message = "⚠️ 請選擇要匯入的 JSON 檔案"
            flash_type = "failure"

    return _render_page(
        request, state, selected_catalyst,
        result, flash_message, flash_type,
    )


def _render_page(
    request: Request,
    state: EnhanceState,
    selected_catalyst: str = "none",
    result: dict | None = None,
    flash_message: str = "",
    flash_type: str = "",
) -> HTMLResponse:
    """渲染 Mako 頁面模板。"""
    progress = {str(k): v for k, v in state.progress.items()}
    state_json = state.model_dump_json()

    template = templates.get_template("crystal_of_atlan/enhance.html")
    html = template.render(
        request=request,
        current_level=state.current_level,
        progress=progress,
        state_json=state_json,
        selected_catalyst=selected_catalyst,
        catalyst_options=CATALYST_OPTIONS,
        result=result,
        flash_message=flash_message,
        flash_type=flash_type,
    )
    return HTMLResponse(html)
