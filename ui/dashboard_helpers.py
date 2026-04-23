import pandas as pd


def safe_get(series_or_dict, key, default="-"):
    try:
        val = series_or_dict[key]
        if pd.isna(val):
            return default
        return val
    except Exception:
        return default


def safe_float(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def pretty_weekly_label(name: str) -> str:
    text = str(name)
    if text in ["warmup", "nan", "None", "-", ""]:
        return "Weekly Warmup（週線暖機中）"
    return text


def pretty_regime_label(name: str) -> str:
    text = str(name)
    if text in ["nan", "None", "-", ""]:
        return "N/A"
    return text


def state_dot_color(name: str) -> str:
    text = str(name)

    if ("多" in text) or ("漲" in text):
        return "#60a5fa"
    if ("空" in text) or ("跌" in text):
        return "#fca5a5"
    if ("盤整" in text) or ("中性" in text):
        return "#fbbf24"
    if ("warmup" in text.lower()) or ("暖機" in text):
        return "#94a3b8"
    if "無事件" in text:
        return "#cbd5e1"
    return "#cbd5e1"