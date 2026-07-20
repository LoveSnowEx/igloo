"""Crystal of Atlan 裝備強化計算器 — 測試。"""

import pytest
from fastapi.testclient import TestClient

from src.modules.crystal_of_atlan.schemas import (
    CalculateRequest,
    CatalystType,
    EnhanceResult,
    EnhanceState,
)
from src.modules.crystal_of_atlan.service import (
    _get_base_rate,
    _optimal_catalyst,
    _truncated_geometric,
    apply_result,
    calculate,
)

# ═══════════════════════════════════════════════
# Service 層 — _optimal_catalyst
# ═══════════════════════════════════════════════

class TestOptimalCatalyst:
    """最佳催化劑選擇 test。"""

    def test_level_0_to_11_best_is_none(self) -> None:
        """+0~+11 失敗無懲罰或效益不高 → 不需要催化劑。"""
        for level in range(12):
            assert _optimal_catalyst(level) == CatalystType.NONE

    def test_level_12_to_13_best_is_stable(self) -> None:
        """+12~+13 會降等 → STABLE 防降等勝出。"""
        for level in (12, 13):
            assert _optimal_catalyst(level) == CatalystType.STABLE

    def test_level_14_best_is_potent(self) -> None:
        """+14 STABLE 不防降等 → POTENT 成功率最高。"""
        assert _optimal_catalyst(14) == CatalystType.POTENT


# ═══════════════════════════════════════════════
# Service 層 — _get_base_rate
# ═══════════════════════════════════════════════

class TestBaseRate:
    """基礎成功率 test。"""

    def test_level_0_is_100_percent(self) -> None:
        assert _get_base_rate(0) == 1.0

    def test_level_10_is_20_percent(self) -> None:
        assert _get_base_rate(10) == pytest.approx(0.20)

    def test_level_14_is_20_percent(self) -> None:
        assert _get_base_rate(14) == pytest.approx(0.20)

    def test_linear_at_level_5(self) -> None:
        assert _get_base_rate(5) == pytest.approx(0.60)

    def test_override_success(self) -> None:
        assert _get_base_rate(5, {5: 0.75}) == 0.75

    def test_override_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match=r"0\.0–1\.0"):
            _get_base_rate(5, {5: 1.5})


# ═══════════════════════════════════════════════
# Service 層 — _truncated_geometric
# ═══════════════════════════════════════════════

class TestTruncatedGeometric:
    """截斷幾何分布 test。"""

    @pytest.mark.parametrize(
        ("p", "remaining", "pity_offset", "expected"),
        [
            # 必定成功：期望值 = 1
            (1.0, 6, 0, 1.0),
            (1.0, 6, 1, 1.0),
            # 必定失敗 → 保底：期望值 = remaining + pity_offset（loop 項為 0）
            (0.0, 3, 0, 3.0),
            (0.0, 3, 1, 4.0),
            # 50% 成功率，remaining=1, pity_offset=0
            # fail_prob after loop: (1-p)^1 = 0.5
            # loop: 1 * 1.0 * 0.5 = 0.5; pity: (1+0) * 0.5 = 0.5 → 期望值 = 1.0
            (0.5, 1, 0, 1.0),
            # 50% 成功率，remaining=1, pity_offset=1
            # loop: 1 * 1.0 * 0.5 = 0.5; pity: (1+1) * 0.5 = 1.0 → 期望值 = 1.5
            (0.5, 1, 1, 1.5),
            # progress=0 → remaining=6，p=0.24
            # 用 calculate 回推驗證
            (0.24, 6, 1, None),  # 僅驗證不拋錯
        ],
    )
    def test_truncated_geometric(
        self,
        p: float,
        remaining: int,
        pity_offset: int,
        expected: float | None,
    ) -> None:
        """截斷幾何分布期望值計算。"""
        result = _truncated_geometric(p, remaining, pity_offset)
        if expected is not None:
            assert result == pytest.approx(expected)
        else:
            # smoke test：應回傳正數
            assert result > 0


# ═══════════════════════════════════════════════
# Service 層 — calculate
# ═══════════════════════════════════════════════

class TestCalculate:
    """計算邏輯 test。"""

    def test_level_0_always_success(self) -> None:
        result = calculate(CalculateRequest(current_level=0, progress=0))
        assert result.effective_success_rate == 1.0
        assert result.use_catalyst is False
        assert result.expected_attempts == 1.0
        assert result.expected_catalysts == 0.0
        assert "+0" in result.catalyst_recommendation

    def test_progress_6_guaranteed(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=10,
                progress=6,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert result.effective_success_rate == 1.0
        assert result.use_catalyst is False
        assert result.expected_attempts == 1.0
        assert result.expected_catalysts == 0.0
        assert "保底" in result.catalyst_recommendation

    def test_normal_with_catalyst(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert result.base_success_rate == pytest.approx(0.20)
        assert result.catalyst_boost == pytest.approx(0.04)
        assert result.effective_success_rate == pytest.approx(0.24)
        assert result.use_catalyst is True
        assert result.expected_attempts > 1.0
        assert result.expected_catalysts > 0.0

    def test_normal_without_catalyst(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.NONE,
            ),
        )
        assert result.use_catalyst is False
        assert result.expected_catalysts == 0.0

    def test_potent_beats_basic(self) -> None:
        basic = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        potent = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.POTENT,
            ),
        )
        assert potent.effective_success_rate > basic.effective_success_rate
        assert potent.expected_attempts < basic.expected_attempts

    def test_effective_rate_capped_at_100(self) -> None:
        """base_rate + boost > 1.0 時 capped at 1.0。"""
        result = calculate(
            CalculateRequest(
                current_level=14,
                progress=0,
                catalyst=CatalystType.POTENT,
                base_success_rates={14: 0.98},
            ),
        )
        assert result.effective_success_rate == 1.0

    def test_level_11_drop_warning(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=11,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert any("降等" in n for n in result.notes)

    def test_level_11_stable_drop_warning(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=11,
                progress=0,
                catalyst=CatalystType.STABLE,
            ),
        )
        assert any("降等" in n for n in result.notes)

    def test_level_12_drop_warning(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=12,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert any("降等" in n for n in result.notes)

    def test_level_14_drop_warning(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=14,
                progress=0,
                catalyst=CatalystType.POTENT,
            ),
        )
        assert any("降等" in n for n in result.notes)

    def test_override_rates(self) -> None:
        result = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.BASIC,
                base_success_rates={10: 0.50},
            ),
        )
        assert result.base_success_rate == pytest.approx(0.50)
        assert result.effective_success_rate == pytest.approx(0.54)

    def test_progress_reduces_expected_attempts(self) -> None:
        r0 = calculate(
            CalculateRequest(
                current_level=10,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        r3 = calculate(
            CalculateRequest(
                current_level=10,
                progress=3,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert r3.expected_attempts < r0.expected_attempts

    def test_progress_5_near_pity(self) -> None:
        """progress=5：只剩一次機會就到保底，期望值應接近 2。"""
        result = calculate(
            CalculateRequest(
                current_level=14,
                progress=5,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert result.expected_attempts < 2.5

    # ── 新建議邏輯 ──

    def test_no_recommendation_when_none_at_level_5(self) -> None:
        """+5 等級選 NONE（最佳）→ 不該有建議。"""
        result = calculate(
            CalculateRequest(
                current_level=5, progress=0, catalyst=CatalystType.NONE,
            ),
        )
        assert result.catalyst_recommendation == ""

    def test_recommend_none_at_level_5_when_using_catalyst(
        self,
    ) -> None:
        """+5 等級已選 POTENT → 應推薦不使用催化劑。"""
        result = calculate(
            CalculateRequest(
                current_level=5, progress=0, catalyst=CatalystType.POTENT,
            ),
        )
        assert "建議不使用催化劑" in result.catalyst_recommendation

    def test_recommend_stable_at_level_12_when_basic(self) -> None:
        """+12 等級選 BASIC → 應推薦 STABLE（防降等優先）。"""
        result = calculate(
            CalculateRequest(
                current_level=12, progress=0, catalyst=CatalystType.BASIC,
            ),
        )
        assert "穩固催化劑" in result.catalyst_recommendation

    def test_no_recommendation_when_already_stable_at_level_12(
        self,
    ) -> None:
        """+12 等級已選 STABLE → 不該有建議。"""
        result = calculate(
            CalculateRequest(
                current_level=12,
                progress=0,
                catalyst=CatalystType.STABLE,
            ),
        )
        assert result.catalyst_recommendation == ""

    def test_recommend_potent_at_level_14_when_basic(self) -> None:
        """+14 選 BASIC → 推薦 POTENT（STABLE 不防 +14 降等）。"""
        result = calculate(
            CalculateRequest(
                current_level=14, progress=0, catalyst=CatalystType.BASIC,
            ),
        )
        assert "強效催化劑" in result.catalyst_recommendation

    def test_no_recommendation_when_already_potent_at_level_14(
        self,
    ) -> None:
        """+14 等級已選 POTENT → 不該有建議。"""
        result = calculate(
            CalculateRequest(
                current_level=14,
                progress=0,
                catalyst=CatalystType.POTENT,
            ),
        )
        assert result.catalyst_recommendation == ""

    # ── 策略提示 notes ──

    @pytest.mark.parametrize(
        ("level", "catalyst", "expected_substring"),
        [
            # 無需使用催化劑
            (5, CatalystType.BASIC, "無需使用催化劑"),
            (11, CatalystType.BASIC, "無需使用催化劑"),
            # 穩固催化劑可防止降等
            (12, CatalystType.STABLE, "穩固催化劑可防止降等"),
            (13, CatalystType.STABLE, "穩固催化劑可防止降等"),
            # 強效催化劑建議
            (14, CatalystType.POTENT, "建議使用強效催化劑"),
        ],
    )
    def test_notes_strategy_tips(
        self,
        level: int,
        catalyst: CatalystType,
        expected_substring: str,
    ) -> None:
        """各等級策略提示 notes 符合預期。"""
        result = calculate(
            CalculateRequest(
                current_level=level,
                progress=0,
                catalyst=catalyst,
            ),
        )
        assert any(
            expected_substring in n for n in result.notes
        )

    @pytest.mark.parametrize("level", [10, 14])
    def test_notes_stable_clarification_shown(
        self, level: int,
    ) -> None:
        """+10 和 +14 顯示穩固催化劑機制說明。"""
        result = calculate(
            CalculateRequest(
                current_level=level,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert any(
            "僅 +11～+13 具防降等效果" in n
            for n in result.notes
        ), f"level {level} 缺少 STABLE 機制說明"

    @pytest.mark.parametrize("level", [11, 12, 13])
    def test_notes_stable_clarification_hidden(
        self, level: int,
    ) -> None:
        """+11~+13 不顯示穩固催化劑機制說明。"""
        result = calculate(
            CalculateRequest(
                current_level=level,
                progress=0,
                catalyst=CatalystType.BASIC,
            ),
        )
        assert not any(
            "僅 +11～+13 具防降等效果" in n
            for n in result.notes
        ), f"level {level} 不該有 STABLE 機制說明"


# ═══════════════════════════════════════════════
# Service 層 — apply_result
# ═══════════════════════════════════════════════

def _state(level: int = 5, **progress: int) -> EnhanceState:
    """建立測試用 EnhanceState。"""
    return EnhanceState(
        current_level=level,
        progress={int(k): v for k, v in progress.items()},
    )


class TestApplyResult:
    """狀態轉換 test。"""

    def test_success_levels_up(self) -> None:
        state = _state(5, **{"5": 3})
        result = apply_result(
            state,
            EnhanceResult.SUCCESS,
            CatalystType.BASIC,
        )
        assert result.current_level == 6
        assert result.progress[5] == 0

    def test_success_at_max_stays(self) -> None:
        state = _state(14, **{"14": 3})
        result = apply_result(
            state,
            EnhanceResult.SUCCESS,
            CatalystType.BASIC,
        )
        assert result.current_level == 14

    def test_failure_no_penalty_at_5(self) -> None:
        state = _state(5, **{"5": 2})
        result = apply_result(
            state,
            EnhanceResult.FAILURE,
            CatalystType.BASIC,
        )
        assert result.current_level == 5
        assert result.progress[5] == 3

    # ── 失敗降等矩陣 ──

    @pytest.mark.parametrize(
        ("level", "catalyst", "expected_level"),
        [
            # 降等（非 STABLE 或 STABLE 不防的等級）
            (11, CatalystType.BASIC, 10),
            (12, CatalystType.BASIC, 11),
            (12, CatalystType.POTENT, 11),
            (13, CatalystType.BASIC, 12),
            (14, CatalystType.BASIC, 13),
            (14, CatalystType.POTENT, 13),
            (14, CatalystType.STABLE, 13),
            # 不降等（STABLE 保護 +11~+13）
            (11, CatalystType.STABLE, 11),
            (12, CatalystType.STABLE, 12),
            (13, CatalystType.STABLE, 13),
        ],
    )
    def test_failure_drop_matrix(
        self,
        level: int,
        catalyst: CatalystType,
        expected_level: int,
    ) -> None:
        """失敗降等矩陣：驗證各等級×催化劑組合的降等行為。"""
        state = _state(level, **{str(level): 3})
        result = apply_result(
            state,
            EnhanceResult.FAILURE,
            catalyst,
        )
        assert result.current_level == expected_level
        assert result.progress[level] == 4

    def test_auto_init_missing_progress(self) -> None:
        """progress dict 缺少目前等級 key 時自動初始化。"""
        state = EnhanceState(current_level=5, progress={})
        result = apply_result(
            state,
            EnhanceResult.FAILURE,
            CatalystType.BASIC,
        )
        assert result.progress[5] == 1
# ═══════════════════════════════════════════════
# API 端點 test
# ═══════════════════════════════════════════════

class TestCalculateEndpoint:
    """POST /api/crystal-of-atlan/calculate"""

    def test_valid_request(self, client: TestClient) -> None:
        resp = client.post(
            "/api/crystal-of-atlan/calculate",
            json={
                "current_level": 10,
                "progress": 0,
                "catalyst": "basic",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_level"] == 10
        assert "expected_attempts" in data

    def test_invalid_level_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/crystal-of-atlan/calculate",
            json={
                "current_level": 20,
                "progress": 0,
            },
        )
        assert resp.status_code == 422


class TestRecordEndpoint:
    """POST /api/crystal-of-atlan/record"""

    def test_records_success(self, client: TestClient) -> None:
        state = EnhanceState(current_level=5, progress={5: 2})
        resp = client.post(
            "/api/crystal-of-atlan/record",
            json={
                "state": state.model_dump(),
                "result": "success",
                "catalyst": "basic",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["current_level"] == 6


class TestExportEndpoint:
    """POST /api/crystal-of-atlan/export"""

    def test_returns_download(self, client: TestClient) -> None:
        state = EnhanceState(current_level=10, progress={10: 3})
        resp = client.post(
            "/api/crystal-of-atlan/export",
            json=state.model_dump(),
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.json()["current_level"] == 10


class TestImportEndpoint:
    """POST /api/crystal-of-atlan/import"""

    def test_imports_json(self, client: TestClient) -> None:
        state = EnhanceState(current_level=8, progress={8: 2})
        content = state.model_dump_json()
        resp = client.post(
            "/api/crystal-of-atlan/import",
            files={"file": ("state.json", content, "application/json")},
        )
        assert resp.status_code == 200
        assert resp.json()["state"]["current_level"] == 8


    def test_imports_invalid_json(self, client: TestClient) -> None:
        """匯入無效 JSON 應回傳 400。"""
        resp = client.post(
            "/api/crystal-of-atlan/import",
            files={"file": ("bad.json", b"not json", "application/json")},
        )
        assert resp.status_code == 400

    def test_imports_invalid_state_data(self, client: TestClient) -> None:
        """匯入有效 JSON 但結構不符應回傳 422。"""
        resp = client.post(
            "/api/crystal-of-atlan/import",
            files={
                "file": (
                    "state.json",
                    b'{"current_level": 20, "progress": {}}',
                    "application/json",
                ),
            },
        )
        assert resp.status_code == 422


class TestPageEndpoint:
    """GET/POST /crystal-of-atlan"""

    def test_get_returns_html(self, client: TestClient) -> None:
        resp = client.get("/crystal-of-atlan")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "晶核裝備強化計算器" in resp.text

    def test_calculate_renders_result(self, client: TestClient) -> None:
        state = EnhanceState(current_level=10, progress={10: 0})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "calculate",
                "current_level": "10",
                "catalyst": "basic",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "期望嘗試次數" in resp.text

    def test_record_success_levels_up(
        self, client: TestClient,
    ) -> None:
        """記錄強化成功：等級應 +1。"""
        state = EnhanceState(current_level=10, progress={10: 2})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "record_success",
                "current_level": "10",
                "catalyst": "basic",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "強化成功" in resp.text
        assert "+11" in resp.text

    def test_record_failure_increments_progress(
        self, client: TestClient,
    ) -> None:
        """記錄強化失敗：進度應 +1。"""
        state = EnhanceState(current_level=5, progress={5: 2})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "record_failure",
                "current_level": "5",
                "catalyst": "basic",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "強化失敗" in resp.text
        assert "進度 +1" in resp.text

    def test_record_failure_drops_level(
        self, client: TestClient,
    ) -> None:
        """記錄強化失敗於 +12 用 BASIC：應顯示降等。"""
        state = EnhanceState(current_level=12, progress={12: 3})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "record_failure",
                "current_level": "12",
                "catalyst": "basic",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "降等" in resp.text

    def test_export_returns_download(
        self, client: TestClient,
    ) -> None:
        """匯出按鈕應回傳 JSON 下載。"""
        state = EnhanceState(current_level=10, progress={10: 3})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "export",
                "current_level": "10",
                "catalyst": "basic",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert resp.json()["current_level"] == 10

    def test_import_uploads_json(
        self, client: TestClient,
    ) -> None:
        """匯入 JSON：無檔案時應顯示提示。（TestClient 混合 data+files
        無法正確傳遞 UploadFile，完整上傳流程由瀏覽器端點驗證）"""
        state = EnhanceState(current_level=10, progress={})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "import",
                "state_json": state.model_dump_json(),
                "current_level": "10",
                "catalyst": "none",
            },
        )
        assert resp.status_code == 200
        assert "請選擇要匯入的 JSON 檔案" in resp.text

    def test_parse_error_shows_flash(self, client: TestClient) -> None:
        """無效的 progress 欄位應顯示錯誤訊息。"""
        state = EnhanceState(current_level=10, progress={})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "calculate",
                "current_level": "10",
                "progress_5": "xyz",
                "catalyst": "none",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "格式無效" in resp.text

    def test_state_from_form_applies_progress(
        self, client: TestClient,
    ) -> None:
        """_state_from_form 正確解析 progress 欄位。"""
        state = EnhanceState(current_level=10, progress={})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "calculate",
                "current_level": "10",
                "progress_10": "4",
                "progress_12": "3",
                "catalyst": "none",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "期望嘗試次數" in resp.text

    # ── 催化劑建議 & notes 前端渲染 ──

    def test_recommendation_shown_when_suboptimal(
        self, client: TestClient,
    ) -> None:
        """+12 選 BASIC（非最佳：最佳為 STABLE）→ API 回傳建議。"""
        resp = client.post(
            "/api/crystal-of-atlan/calculate",
            json={
                "current_level": 12,
                "progress": 0,
                "catalyst": "basic",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "穩固催化劑" in data["catalyst_recommendation"]

    def test_recommendation_hidden_when_optimal(
        self, client: TestClient,
    ) -> None:
        """+12 選 STABLE（最佳）→ API 不該回傳建議。"""
        resp = client.post(
            "/api/crystal-of-atlan/calculate",
            json={
                "current_level": 12,
                "progress": 0,
                "catalyst": "stable",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["catalyst_recommendation"] == ""

    def test_notes_rendered_in_page(
        self, client: TestClient,
    ) -> None:
        """+12 API 回傳應包含降等提示與穩固催化劑 notes。"""
        resp = client.post(
            "/api/crystal-of-atlan/calculate",
            json={
                "current_level": 12,
                "progress": 0,
                "catalyst": "basic",
            },
        )
        assert resp.status_code == 200
        notes: list[str] = resp.json()["notes"]
        assert any("降等" in n for n in notes)
        assert any("穩固催化劑可防止降等" in n for n in notes)

    def test_record_failure_no_drop_at_11_with_stable(
        self, client: TestClient,
    ) -> None:
        """+11 用 STABLE 失敗：頁面不顯示降等，等級不變。"""
        state = EnhanceState(current_level=11, progress={11: 3})
        resp = client.post(
            "/crystal-of-atlan",
            data={
                "action": "record_failure",
                "current_level": "11",
                "catalyst": "stable",
                "state_json": state.model_dump_json(),
            },
        )
        assert resp.status_code == 200
        assert "強化失敗" in resp.text
        assert "降等" not in resp.text
        assert "+11" in resp.text
