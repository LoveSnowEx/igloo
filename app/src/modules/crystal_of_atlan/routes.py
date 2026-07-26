"""Crystal of Atlan enhancement calculator — API endpoints."""

import json

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .schemas import (
    CalculateRequest,
    CalculateResponse,
    EnhanceState,
    ImportResponse,
    RecordResultRequest,
)
from .service import apply_result, calculate

router = APIRouter(prefix="/api/crystal-of-atlan", tags=["Crystal of Atlan"])


@router.post("/calculate", response_model=CalculateResponse)
async def calculate_endpoint(request: CalculateRequest) -> CalculateResponse:
    """Calculate enhancement strategy."""
    return calculate(request)


@router.post("/record", response_model=EnhanceState)
async def record_endpoint(request: RecordResultRequest) -> EnhanceState:
    """Record enhancement result and update state."""
    return apply_result(request.state, request.result, request.catalyst)


@router.post("/export")
async def export_endpoint(state: EnhanceState):
    """Export enhancement state as JSON download."""
    return JSONResponse(
        content=state.model_dump(),
        headers={
            "Content-Disposition": (
                "attachment; filename=crystal-of-atlan-enhance-state.json"
            ),
        },
    )


@router.post("/import", response_model=ImportResponse)
async def import_endpoint(file: UploadFile) -> ImportResponse:
    """Import enhancement state JSON file."""
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
        message=f"Successfully imported (current level: +{state.current_level})",
    )
