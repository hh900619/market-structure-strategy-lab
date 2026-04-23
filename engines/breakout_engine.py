import pandas as pd


# =========================================================
# Helper
# =========================================================
def _contains_any(text: str, keywords: list[str]) -> bool:
    text = str(text)
    return any(k in text for k in keywords)


# =========================================================
# Mid regime scoring
# breakout 哲學：
# - 方向一致最重要
# - 高波動不一定是壞事
# - 混亂若方向一致，只小扣；若方向相反，再重扣
# =========================================================
def _score_mid_for_breakout(regime_name: str, direction: str) -> int:
    text = str(regime_name)

    if direction == "long":
        # 方向主體
        if _contains_any(text, ["急漲", "緩漲", "偏多"]):
            score = 2
        elif _contains_any(text, ["中性盤整", "壓縮中性", "中性"]):
            score = 0
        elif _contains_any(text, ["急跌", "緩跌", "偏空"]):
            score = -2
        else:
            score = 0

        # 結構微調
        if "混亂" in text:
            # 同方向混亂：小扣
            if score > 0:
                score -= 1
            # 反方向混亂：再扣
            elif score < 0:
                score -= 1

        # 波動微調：順勢 breakout 不怕擴張，只在反方向時多扣
        if "高波動" in text:
            if score < 0:
                score -= 1
            elif score > 0:
                score += 0  # 不加也不扣

        # 壓縮偏多 / 壓縮緩漲 對多 breakout 有利
        if "壓縮" in text and _contains_any(text, ["偏多", "漲"]):
            score += 1

        return int(score)

    if direction == "short":
        if _contains_any(text, ["急跌", "緩跌", "偏空"]):
            score = 2
        elif _contains_any(text, ["中性盤整", "壓縮中性", "中性"]):
            score = 0
        elif _contains_any(text, ["急漲", "緩漲", "偏多"]):
            score = -2
        else:
            score = 0

        if "混亂" in text:
            if score > 0:
                score -= 1
            elif score < 0:
                score -= 1

        if "高波動" in text:
            if score < 0:
                score -= 1
            elif score > 0:
                score += 0

        if "壓縮" in text and _contains_any(text, ["偏空", "跌"]):
            score += 1

        return int(score)

    return 0


# =========================================================
# Weekly scoring
# weekly 是慢背景：
# - 主要看大方向是否明顯反對
# - 不要過度主導 breakout
# =========================================================
def _score_weekly_for_breakout(weekly_bg: str, direction: str) -> int:
    text = str(weekly_bg)

    if "暖機" in text:
        return 0

    if direction == "long":
        if _contains_any(text, ["偏多", "緩漲", "急漲"]):
            score = 2
        elif _contains_any(text, ["中性", "盤整"]):
            score = 0
        elif _contains_any(text, ["偏空", "緩跌", "急跌"]):
            score = -2
        else:
            score = 0

        if "混亂" in text and score < 0:
            score -= 1

        if "壓縮" in text and _contains_any(text, ["偏多", "漲"]):
            score += 1

        return int(score)

    if direction == "short":
        if _contains_any(text, ["偏空", "緩跌", "急跌"]):
            score = 2
        elif _contains_any(text, ["中性", "盤整"]):
            score = 0
        elif _contains_any(text, ["偏多", "緩漲", "急漲"]):
            score = -2
        else:
            score = 0

        if "混亂" in text and score < 0:
            score -= 1

        if "壓縮" in text and _contains_any(text, ["偏空", "跌"]):
            score += 1

        return int(score)

    return 0


# =========================================================
# Fast event scoring
# fast 對 breakout 很重要，但要有方向性：
# - 同方向 burst：強加分
# - 反方向 burst：強扣分
# - Structural Break 不一律視為壞，要看方向
# - Volatility Shock 只小扣
# =========================================================
def _score_fast_for_breakout(fast_event: str, direction: str) -> int:
    text = str(fast_event)

    if "無事件" in text:
        return 0

    if direction == "long":
        if _contains_any(text, ["Upward Burst", "向上爆發"]):
            return 3
        if _contains_any(text, ["Downward Burst", "向下爆發"]):
            return -3
        if _contains_any(text, ["Structural Break", "結構破壞"]):
            # breakout 很可能就伴隨結構改寫，先保守負分，不重扣
            return -1
        if _contains_any(text, ["Volatility Shock", "波動衝擊"]):
            return -1

    if direction == "short":
        if _contains_any(text, ["Downward Burst", "向下爆發"]):
            return 3
        if _contains_any(text, ["Upward Burst", "向上爆發"]):
            return -3
        if _contains_any(text, ["Structural Break", "結構破壞"]):
            return -1
        if _contains_any(text, ["Volatility Shock", "波動衝擊"]):
            return -1

    return 0


# =========================================================
# Strictness thresholds
# 調整成更平滑：
# low：較寬鬆
# medium：平衡
# high：保守但不僵硬
# =========================================================
STRICTNESS_CONFIG = {
    "low": {
        "entry_allow": 1,
        "entry_cautious": 0,
        "hold_keep": 0,
        "hold_reduce": -1,
    },
    "medium": {
        "entry_allow": 2,
        "entry_cautious": 0,
        "hold_keep": 1,
        "hold_reduce": 0,
    },
    "high": {
        "entry_allow": 3,
        "entry_cautious": 1,
        "hold_keep": 2,
        "hold_reduce": 1,
    },
}


# =========================================================
# Decision helpers
# =========================================================
def _entry_decision(score: int, strictness: str) -> str:
    cfg = STRICTNESS_CONFIG[strictness]
    if score >= cfg["entry_allow"]:
        return "allow"
    if score >= cfg["entry_cautious"]:
        return "cautious"
    return "block"


def _hold_decision(score: int, strictness: str) -> str:
    cfg = STRICTNESS_CONFIG[strictness]
    if score >= cfg["hold_keep"]:
        return "hold"
    if score >= cfg["hold_reduce"]:
        return "reduce"
    return "exit"


def _size_hint_from_entry(entry_decision: str, score: int) -> float:
    if entry_decision == "allow" and score >= 5:
        return 1.25
    if entry_decision == "allow":
        return 1.0
    if entry_decision == "cautious":
        return 0.5
    return 0.0


def _size_hint_from_hold(hold_decision: str, score: int) -> float:
    if hold_decision == "hold" and score >= 5:
        return 1.25
    if hold_decision == "hold":
        return 1.0
    if hold_decision == "reduce":
        return 0.5
    return 0.0


# =========================================================
# Reason helper
# =========================================================
def _reason_from_entry(direction: str, decision: str) -> str:
    if direction == "long":
        if decision == "allow":
            return "long_entry_allowed"
        if decision == "cautious":
            return "long_entry_cautious"
        return "long_entry_blocked"

    if direction == "short":
        if decision == "allow":
            return "short_entry_allowed"
        if decision == "cautious":
            return "short_entry_cautious"
        return "short_entry_blocked"

    return "flat"


def _reason_from_hold(direction: str, decision: str) -> str:
    if direction == "long":
        if decision == "hold":
            return "long_hold_ok"
        if decision == "reduce":
            return "long_hold_reduce"
        return "long_exit_regime"

    if direction == "short":
        if decision == "hold":
            return "short_hold_ok"
        if decision == "reduce":
            return "short_hold_reduce"
        return "short_exit_regime"

    return "flat"


# =========================================================
# Main engine
# =========================================================
def apply_breakout_engine(
    state_df: pd.DataFrame,
    base_signal: pd.Series,
    strictness: str = "medium",
) -> pd.DataFrame:
    df = state_df.copy()
    df["base_signal"] = base_signal.reindex(df.index).fillna(0.0).astype(float)

    engine_signal = []
    size_hints = []
    entry_decisions = []
    hold_decisions = []
    reasons = []

    long_entry_ok_list = []
    short_entry_ok_list = []
    long_hold_ok_list = []
    short_hold_ok_list = []

    prev_engine_pos = 0.0

    for _, row in df.iterrows():
        base_sig = float(row["base_signal"])

        mid_name = row.get("mid_regime_name", "")
        weekly_bg = row.get("weekly_weekly_background_name", "")
        fast_event = row.get("fast_event_display", "無事件")

        long_score = (
            _score_mid_for_breakout(mid_name, "long")
            + _score_weekly_for_breakout(weekly_bg, "long")
            + _score_fast_for_breakout(fast_event, "long")
        )
        short_score = (
            _score_mid_for_breakout(mid_name, "short")
            + _score_weekly_for_breakout(weekly_bg, "short")
            + _score_fast_for_breakout(fast_event, "short")
        )

        long_entry_dec = _entry_decision(long_score, strictness)
        short_entry_dec = _entry_decision(short_score, strictness)

        long_hold_dec = _hold_decision(long_score, strictness)
        short_hold_dec = _hold_decision(short_score, strictness)

        long_entry_ok = long_entry_dec in ["allow", "cautious"]
        short_entry_ok = short_entry_dec in ["allow", "cautious"]
        long_hold_ok = long_hold_dec in ["hold", "reduce"]
        short_hold_ok = short_hold_dec in ["hold", "reduce"]

        out_sig = 0.0
        size_hint = 0.0
        entry_decision = "flat"
        hold_decision = "flat"
        reason = "flat"

        # -------------------------------------------------
        # base flat => engine 也 flat
        # -------------------------------------------------
        if base_sig == 0.0:
            out_sig = 0.0
            size_hint = 0.0
            entry_decision = "flat"
            hold_decision = "flat"
            reason = "flat"

        # -------------------------------------------------
        # base wants long
        # -------------------------------------------------
        elif base_sig == 1.0:
            entry_decision = long_entry_dec
            hold_decision = long_hold_dec

            if prev_engine_pos == 1.0:
                out_sig = 1.0 if long_hold_dec in ["hold", "reduce"] else 0.0
                size_hint = _size_hint_from_hold(long_hold_dec, long_score) if out_sig != 0.0 else 0.0
                reason = _reason_from_hold("long", long_hold_dec)
            else:
                if long_entry_dec in ["allow", "cautious"]:
                    out_sig = 1.0
                    size_hint = _size_hint_from_entry(long_entry_dec, long_score)
                else:
                    out_sig = 0.0
                    size_hint = 0.0
                reason = _reason_from_entry("long", long_entry_dec)

        # -------------------------------------------------
        # base wants short
        # -------------------------------------------------
        elif base_sig == -1.0:
            entry_decision = short_entry_dec
            hold_decision = short_hold_dec

            if prev_engine_pos == -1.0:
                out_sig = -1.0 if short_hold_dec in ["hold", "reduce"] else 0.0
                size_hint = _size_hint_from_hold(short_hold_dec, short_score) if out_sig != 0.0 else 0.0
                reason = _reason_from_hold("short", short_hold_dec)
            else:
                if short_entry_dec in ["allow", "cautious"]:
                    out_sig = -1.0
                    size_hint = _size_hint_from_entry(short_entry_dec, short_score)
                else:
                    out_sig = 0.0
                    size_hint = 0.0
                reason = _reason_from_entry("short", short_entry_dec)

        prev_engine_pos = out_sig

        engine_signal.append(out_sig)
        size_hints.append(size_hint)
        entry_decisions.append(entry_decision)
        hold_decisions.append(hold_decision)
        reasons.append(reason)

        long_entry_ok_list.append(long_entry_ok)
        short_entry_ok_list.append(short_entry_ok)
        long_hold_ok_list.append(long_hold_ok)
        short_hold_ok_list.append(short_hold_ok)

    out = df.copy()
    out["engine_strictness"] = strictness
    out["long_entry_ok"] = long_entry_ok_list
    out["short_entry_ok"] = short_entry_ok_list
    out["long_hold_ok"] = long_hold_ok_list
    out["short_hold_ok"] = short_hold_ok_list
    out["entry_decision"] = entry_decisions
    out["hold_decision"] = hold_decisions
    out["engine_signal"] = engine_signal
    out["size_hint"] = size_hints
    out["engine_reason"] = reasons

    return out