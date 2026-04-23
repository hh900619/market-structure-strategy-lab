import pandas as pd
import streamlit as st


def render_signal_diagnostics(base_signal: pd.Series, engine_signal: pd.Series):
    """
    目前新版 Strategy Lab 不一定會用到，
    但先保留成較容易理解的版本。
    """
    base_nonzero = int((base_signal != 0).sum())
    engine_nonzero = int((engine_signal != 0).sum())
    filtered_out = base_nonzero - engine_nonzero
    pass_ratio = (engine_nonzero / base_nonzero) if base_nonzero > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("原始策略持倉訊號數", f"{base_nonzero}")
    with c2:
        st.metric("Engine 保留訊號數", f"{engine_nonzero}")
    with c3:
        st.metric("被 Engine 擋掉", f"{filtered_out}")
    with c4:
        st.metric("訊號保留比例", f"{pass_ratio:.2%}")


def render_engine_reason_section(eng_df: pd.DataFrame):
    reason_counts = (
        eng_df["engine_reason"]
        .astype(str)
        .value_counts(dropna=False)
        .rename_axis("原因")
        .reset_index(name="次數")
    )

    st.dataframe(reason_counts, use_container_width=True)

    with st.expander("這些 Engine 原因代表什麼？", expanded=False):
        st.markdown(
            """
這一區是在告訴你：Engine 平常主要怎麼處理原始策略的訊號。

你最常會看到的幾類意思如下：

- **flat**  
  代表原始策略當下本來就沒有持倉，所以 Engine 也沒有動作。

- **long_entry_allowed / short_entry_allowed**  
  代表原始策略想進場，而且 Engine 允許這次進場。

- **long_entry_cautious / short_entry_cautious**  
  代表 Engine 沒有完全擋掉這次進場，但認為背景不是最理想，屬於較保守看待。

- **long_entry_blocked / short_entry_blocked**  
  代表原始策略本來想進場，但 Engine 認為當下市場背景不適合，因此直接擋掉。

- **long_hold_ok / short_hold_ok**  
  代表已經持有中的部位，Engine 認為可以繼續持有。

- **long_hold_reduce / short_hold_reduce**  
  代表 Engine 認為雖然不一定要立刻退出，但持倉品質下降，應該用較保守方式看待。

- **long_exit_regime / short_exit_regime**  
  代表原本持有中的部位，因為市場背景改變，Engine 傾向提早退出。

---

你不需要把每個代碼都背起來，重點是看：

1. Engine 比較常放行，還是比較常阻擋  
2. Engine 主要是在進場時介入，還是在持倉期間介入  
3. 哪一類原因出現最多，是否代表這個 Engine 的風格太單一
"""
        )


def render_signal_preview_section(
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series,
    eng_df: pd.DataFrame,
):
    preview = pd.DataFrame(index=price_df.index)
    preview["收盤價"] = price_df["Close"].astype(float)
    preview["原始策略訊號"] = base_signal.reindex(price_df.index).astype(float)
    preview["Engine 後訊號"] = engine_signal.reindex(price_df.index).astype(float)
    preview["Engine 判斷"] = eng_df["engine_reason"].reindex(price_df.index).astype(str)

    if "mid_regime_name" in state_df.columns:
        preview["中期市場狀態"] = state_df["mid_regime_name"].reindex(price_df.index)

    if "weekly_weekly_background_name" in state_df.columns:
        preview["週線背景"] = state_df["weekly_weekly_background_name"].reindex(price_df.index)

    if "fast_event_display" in state_df.columns:
        preview["快層事件"] = state_df["fast_event_display"].reindex(price_df.index)

    # 使用者看最近區段，保留最近 30 根
    preview = preview.tail(30).copy()

    # index 轉成比較直觀的日期欄
    preview = preview.reset_index().rename(columns={"index": "日期"})
    if "Date" in preview.columns:
        preview = preview.rename(columns={"Date": "日期"})

    st.dataframe(preview, use_container_width=True)

    with st.expander("怎麼看這個最近訊號觀察表？", expanded=False):
        st.markdown(
            """
這張表不是要你直接看整體績效，而是拿來做局部觀察。

你可以這樣看：

- **原始策略訊號**  
  代表策略本來想怎麼做。  
  `1` 通常表示做多，`-1` 表示做空，`0` 表示空手。

- **Engine 後訊號**  
  代表加入 Engine 後，最後真正保留下來的持倉狀態。

- **Engine 判斷**  
  代表 Engine 當時為什麼放行、阻擋、續抱或退出。

- **中期市場狀態 / 週線背景 / 快層事件**  
  幫你理解：當時市場背景是什麼，Engine 為什麼會這樣判斷。

這張表最適合搭配上方交易圖一起看。  
先在圖上看到某次進場或被擋掉的訊號，再回到這裡看當時背景與原因，會最容易理解。
"""
        )