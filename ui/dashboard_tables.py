import pandas as pd


def make_recent_state_table(
    state_df: pd.DataFrame,
    pretty_weekly_label,
) -> pd.DataFrame:
    cols = [
        "Close",
        "short_regime_name",
        "mid_regime_name",
        "long_regime_name",
        "weekly_mid_regime_name",
        "weekly_weekly_background_name",
        "fast_event_display",
    ]
    use_cols = [c for c in cols if c in state_df.columns]
    out = state_df[use_cols].tail(20).copy()

    if "weekly_weekly_background_name" in out.columns:
        out["weekly_weekly_background_name"] = (
            out["weekly_weekly_background_name"].astype(str).map(pretty_weekly_label)
        )

    return out