"""Crystal of Atlan 裝備強化計算器 — 請求/回應 schema。"""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class CatalystType(StrEnum):
    """催化劑類型。"""

    NONE = "none"
    BASIC = "basic"
    STABLE = "stable"
    POTENT = "potent"


CATALYST_BOOST: dict[CatalystType, float] = {
    CatalystType.NONE: 0.0,
    CatalystType.BASIC: 0.04,
    CatalystType.STABLE: 0.04,
    CatalystType.POTENT: 0.07,
}

CATALYST_LABELS: dict[CatalystType, str] = {
    CatalystType.NONE: "不使用",
    CatalystType.BASIC: "催化劑（粉）",
    CatalystType.STABLE: "穩固催化劑（粉）",
    CatalystType.POTENT: "強效催化劑（金）",
}


class EnhanceResult(StrEnum):
    """強化結果。"""

    SUCCESS = "success"
    FAILURE = "failure"


class CalculateRequest(BaseModel):
    """計算請求。"""

    current_level: int = Field(ge=0, le=14, description="目前強化等級（0–14）")
    progress: int = Field(
        ge=0, le=6, description="目前等級已失敗次數（0–6，6 表示下一次保底）",
    )
    catalyst: CatalystType = Field(
        default=CatalystType.NONE, description="使用的催化劑類型",
    )
    base_success_rates: dict[int, float] | None = Field(
        default=None, description="覆蓋預設基礎成功率（等級 → 成功率，0.0–1.0）",
    )

    @field_validator("base_success_rates")
    @classmethod
    def _check_base_success_rates_range(
        cls, v: dict[int, float] | None,
    ) -> dict[int, float] | None:
        """驗證每個成功率在 0.0–1.0 之間。"""
        if v is None:
            return v
        for level, rate in v.items():
            if not 0.0 <= rate <= 1.0:
                msg = (
                    f"base_success_rates[{level}] 必須在 0.0–1.0 之間，"
                    f"收到 {rate}"
                )
                raise ValueError(msg)
        return v


class CalculateResponse(BaseModel):
    """計算結果。"""

    current_level: int
    progress: int
    base_success_rate: float
    catalyst_boost: float
    effective_success_rate: float
    use_catalyst: bool
    catalyst_recommendation: str
    expected_attempts: float
    expected_catalysts: float
    notes: list[str]


class EnhanceState(BaseModel):
    """完整強化狀態（用於匯入/匯出與狀態追蹤）。"""

    current_level: int = Field(ge=0, le=14, description="目前強化等級")
    progress: dict[int, int] = Field(
        default_factory=dict,
        description="各等級已失敗次數（等級 → 次數，0–6）",
    )

    @field_validator("progress")
    @classmethod
    def _check_progress_range(
        cls, v: dict[int, int],
    ) -> dict[int, int]:
        """驗證每個進度值在 0–6 之間，等級鍵在 0–14 之間。"""
        for level, count in v.items():
            if not 0 <= level <= 14:
                msg = (
                    f"progress[{level}] 等級必須在 0–14 之間"
                )
                raise ValueError(msg)
            if not 0 <= count <= 6:
                msg = (
                    f"progress[{level}] 必須在 0–6 之間，收到 {count}"
                )
                raise ValueError(msg)
        return v


class RecordResultRequest(BaseModel):
    """記錄強化結果請求。"""

    state: EnhanceState
    result: EnhanceResult
    catalyst: CatalystType


class ImportResponse(BaseModel):
    """匯入回應。"""

    state: EnhanceState
    message: str
