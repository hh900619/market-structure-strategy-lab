import pandas as pd


def safe_text(x):
    if pd.isna(x):
        return "-"
    return str(x)


def safe_conf(x):
    if pd.isna(x):
        return "-"
    return f"{float(x):.3f}"


def safe_pct(x):
    if pd.isna(x):
        return "-"
    return f"{float(x) * 100:.2f}%"


def safe_float(x):
    if pd.isna(x):
        return 0.0
    return float(x)


def confidence_level_label(x):
    if pd.isna(x):
        return "-"
    x = float(x)
    if x >= 0.55:
        return "高"
    if x >= 0.35:
        return "中"
    return "低"


def confidence_emoji(x):
    if pd.isna(x):
        return "⚪"
    x = float(x)
    if x >= 0.55:
        return "🟢"
    if x >= 0.35:
        return "🟡"
    return "🔴"

def direction_label(x):
    mapping = {
        "up": "上行",
        "neutral": "中性",
        "down": "下行",
    }
    return mapping.get(str(x), safe_text(x))


def structure_label(x):
    mapping = {
        "clean": "乾淨",
        "neutral": "普通",
        "messy": "混亂",
    }
    return mapping.get(str(x), safe_text(x))


def impulse_label(x):
    mapping = {
        "high": "強",
        "medium": "中",
        "low": "弱",
    }
    return mapping.get(str(x), safe_text(x))


def volatility_label(x):
    mapping = {
        "compressed": "壓縮",
        "normal": "正常",
        "expanded": "擴張",
    }
    return mapping.get(str(x), safe_text(x))


def regime_tone_emoji(name: str) -> str:
    text = str(name)
    if any(k in text for k in ["急漲", "緩漲", "偏多"]):
        return "🟢"
    if any(k in text for k in ["急跌", "緩跌", "偏空"]):
        return "🔴"
    if "盤整" in text or "中性" in text:
        return "🟡"
    return "⚪"


def risk_emoji(text: str) -> str:
    text = str(text)
    if any(k in text for k in ["結構破壞", "高風險", "顯著降低", "防守"]):
        return "🔴"
    if any(k in text for k in ["波動衝擊", "保守", "降低", "混亂"]):
        return "🟡"
    return "🟢"


def classify_mid_regime_group(name: str) -> str:
    text = str(name)
    if any(k in text for k in ["急跌", "緩跌", "偏空"]):
        return "bear"
    if any(k in text for k in ["急漲", "緩漲", "偏多"]):
        return "bull"
    return "range"


def build_market_summary_text(latest: pd.Series) -> str:
    short_name = safe_text(latest.get("short_regime_name"))
    mid_name = safe_text(latest.get("mid_regime_name"))
    long_name = safe_text(latest.get("long_regime_name"))
    weekly_name = safe_text(latest.get("weekly_weekly_background_name"))
    fast_name = safe_text(latest.get("fast_event_display"))

    return (
        f"目前市場短期是「{short_name}」，中期是「{mid_name}」，長期是「{long_name}」。"
        f"週線大背景為「{weekly_name}」，Fast 事件是「{fast_name}」，"
    )


def build_simple_takeaway(latest: pd.Series) -> str:
    mid_name = safe_text(latest.get("mid_regime_name"))
    weekly_name = safe_text(latest.get("weekly_weekly_background_name"))
    fast_name = safe_text(latest.get("fast_event_display"))

    return (
        f"中期主狀態：{mid_name}；"
        f"週線背景：{weekly_name}；"
        f"短期事件：{fast_name}；"
    )


def slow_explanation(prefix: str, latest: pd.Series) -> str:
    d = direction_label(latest.get(f"{prefix}_direction_state"))
    s = structure_label(latest.get(f"{prefix}_structure_state"))
    i = impulse_label(latest.get(f"{prefix}_impulse_state"))
    v = volatility_label(latest.get(f"{prefix}_volatility_state"))
    return f"這代表此週期目前方向偏{d}、結構偏{s}、推進力道偏{i}、波動環境偏{v}。"


def weekly_explanation(latest: pd.Series) -> str:
    d = direction_label(latest.get("weekly_mid_direction_state"))
    s = structure_label(latest.get("weekly_mid_structure_state"))
    v = volatility_label(latest.get("weekly_mid_volatility_state"))
    return f"週線背景主要在描述更高時間尺度的大方向。目前週線中期方向偏{d}，結構偏{s}，波動偏{v}。"