"""Crystal of Atlan 裝備強化計算器 — 核心計算邏輯。"""

from app.schemas.crystal_of_atlan.enhance import (
    CATALYST_BOOST,
    CATALYST_LABELS,
    CalculateRequest,
    CalculateResponse,
    CatalystType,
    EnhanceResult,
    EnhanceState,
)


def _get_base_rate(
    level: int, overrides: dict[int, float] | None = None,
) -> float:
    """取得指定等級的基礎成功率。

    +0: 100%、+1~+10: 線性遞減至 20%、+11~+14: 固定 20%。
    可透過 overrides 覆蓋。
    """
    if overrides and level in overrides:
        rate = overrides[level]
        if not 0.0 <= rate <= 1.0:
            msg = f"成功率必須在 0.0–1.0 之間，收到 {rate}"
            raise ValueError(msg)
        return rate
    if level == 0:
        return 1.0
    if level <= 10:
        return 1.0 - 0.08 * level
    return 0.20


# 催化劑稀有度 → CSS class（前端渲染用）
_CATALYST_RARITY_CLASS: dict[CatalystType, str] = {
    CatalystType.NONE: "",
    CatalystType.BASIC: "catalyst-pink",
    CatalystType.STABLE: "catalyst-pink",
    CatalystType.POTENT: "catalyst-gold",
}


def _optimal_catalyst(level: int) -> CatalystType:
    """各等級的最佳催化劑（直接對照）。

    +0~+11  失敗無懲罰或效益不高 → NONE
            （+11 雖然 STABLE 可防降等，但 1 級損失有限，
             穩固催化劑保留至 +12／+13 更划算）
    +12~+13 穩固催化劑防降等
    +14     強效催化劑拚成功率（穩固不防 +14）
    """
    if level <= 11:
        return CatalystType.NONE
    if level <= 13:
        return CatalystType.STABLE
    return CatalystType.POTENT


def _truncated_geometric(p: float, remaining: int, pity_offset: int = 0) -> float:
    """截斷幾何分布的期望值。

    Args:
        p: 單次成功機率。
        remaining: 保底前可嘗試次數。
        pity_offset: 保底次數偏移（0 = N+1, 1 = N）。

    Returns:
        期望次數。
    """
    expected = 0.0
    fail_prob = 1.0
    for i in range(1, remaining + 1):
        expected += i * fail_prob * p
        fail_prob *= 1.0 - p
    return expected + (remaining + pity_offset) * fail_prob


def calculate(request: CalculateRequest) -> CalculateResponse:
    """計算強化策略。

    根據目前等級、進度次數與催化劑選擇，計算成功率、
    期望嘗試次數、期望催化劑消耗，並給予催化劑使用建議。
    """
    level = request.current_level
    progress = request.progress
    catalyst = request.catalyst
    base_rate = _get_base_rate(level, request.base_success_rates)
    notes: list[str] = []

    # +0 必定成功
    if level == 0:
        return CalculateResponse(
            current_level=level,
            progress=progress,
            base_success_rate=base_rate,
            catalyst_boost=0.0,
            effective_success_rate=1.0,
            use_catalyst=False,
            catalyst_recommendation="+0 必定成功，無需催化劑",
            expected_attempts=1.0,
            expected_catalysts=0.0,
            notes=["+0 必定成功"],
        )

    # 保底：第 7 次保證成功，不使用催化劑
    if progress >= 6:
        return CalculateResponse(
            current_level=level,
            progress=progress,
            base_success_rate=base_rate,
            catalyst_boost=0.0,
            effective_success_rate=1.0,
            use_catalyst=False,
            catalyst_recommendation="保底觸發，必定成功，無需催化劑",
            expected_attempts=1.0,
            expected_catalysts=0.0,
            notes=["保底觸發：第 7 次必定成功，無需催化劑"],
        )

    # 一般情況
    boost = CATALYST_BOOST[catalyst]
    use_catalyst = catalyst != CatalystType.NONE
    p = min(1.0, base_rate + boost) if use_catalyst else base_rate

    # 剩餘保底前可嘗試次數
    remaining = 6 - progress

    # 期望嘗試次數：截斷幾何分布
    expected_attempts = _truncated_geometric(p, remaining, pity_offset=1)

    # 期望催化劑消耗：第 7 次不使用催化劑
    expected_catalysts = (
        _truncated_geometric(p, remaining, pity_offset=0)
        if use_catalyst
        else 0.0
    )

    # 建議文字：只在當前選擇不是最佳催化劑時顯示
    best = _optimal_catalyst(level)
    if catalyst != best:
        if best == CatalystType.NONE:
            recommendation = "建議不使用催化劑"
        else:
            css_class = _CATALYST_RARITY_CLASS[best]
            label = CATALYST_LABELS[best]
            recommendation = (  # nosemgrep: raw-html-format
                f'建議使用 <strong class="{css_class}">{label}</strong>'
            )
    else:
        recommendation = ""

    # 降等提示（+11～+14）
    if 11 <= level <= 14:
        notes.append("⚠ 失敗將導致降等")

    # 策略建議
    if 1 <= level <= 11:
        notes.append("+0～+11 失敗無降級懲罰或效益不高，無需使用催化劑")
    elif 12 <= level <= 13:
        notes.append("穩固催化劑可防止降等")
    elif level == 14:
        notes.append(
            "建議使用強效催化劑，+14 成功率最高",
        )

    # 穩固催化劑機制說明（僅 +11～+13 以外顯示）
    if level <= 10 or level == 14:
        notes.append(
            "穩固催化劑僅 +11～+13 具防降等效果，"
            "其餘等級等同一般催化劑",
        )

    return CalculateResponse(
        current_level=level,
        progress=progress,
        base_success_rate=round(base_rate, 4),
        catalyst_boost=round(boost, 4) if use_catalyst else 0.0,
        effective_success_rate=round(p, 4),
        use_catalyst=use_catalyst,
        catalyst_recommendation=recommendation,
        expected_attempts=round(expected_attempts, 2),
        expected_catalysts=round(expected_catalysts, 2),
        notes=notes,
    )


def apply_result(
    state: EnhanceState, result: EnhanceResult, catalyst: CatalystType,
) -> EnhanceState:
    """根據強化結果更新狀態。

    成功：當前等級進度歸零，等級 +1（上限 14）。
    失敗：進度 +1。
    +11～+14 失敗時降 1 級，唯 +11／+12／+13 搭配穩固催化劑可避免降等。
    """
    level = state.current_level

    # 確保 progress dict 中有當前等級的 key
    if level not in state.progress:
        state.progress[level] = 0

    if result == EnhanceResult.SUCCESS:
        state.progress[level] = 0
        if level < 14:
            state.current_level += 1
        return state

    # 失敗
    state.progress[level] += 1

    # 降等判定：+11~+14 且非穩固催化劑，或 +14
    should_drop = (
        11 <= level <= 14
        and not (catalyst == CatalystType.STABLE and level in (11, 12, 13))
    )
    if should_drop:
        state.current_level = level - 1

    return state
