import streamlit as st


def render_core_card(title: str, state_name: str, desc: str, state_dot_color):
    dot_color = state_dot_color(state_name)

    st.markdown(f"### {title}")
    st.markdown(
        f"<div style='font-size:1.05rem; margin-bottom:0.35rem;'>"
        f"<span style='color:{dot_color}; font-size:1.2rem;'>●</span> {state_name}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption(desc)


def render_current_view_info(regime_view: str, ticker: str, latest, safe_get):
    weekly_source = safe_get(latest, "weekly_weekly_data_source", "-")

    if regime_view == "Mid-term Regime（中期分類）":
        st.caption(
            f"目前主圖顯示：{regime_view}｜資料週期：Daily Bar（日 K）｜資料來源：Yahoo Finance｜Ticker：{ticker}"
        )
        st.caption(
            "這張圖使用日 K 的中期分類來上色，代表目前市場的主要中期結構。"
        )
    else:
        st.caption(
            f"目前主圖顯示：{regime_view}｜資料週期：Weekly Bar（週 K）｜資料來源：{weekly_source}｜Ticker：{ticker}"
        )
        st.caption(
            "這張圖直接使用週 K（1wk）來顯示週線背景層，因此你現在看到的不是日 K，而是真正的週線圖。"
        )
        st.caption(
            "這一層是較慢、較穩定的背景層，用來看更高時間尺度的大方向，不是短線進出場訊號。"
        )