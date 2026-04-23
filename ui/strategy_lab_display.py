import streamlit as st


def render_backtest_summary(title: str, perf: dict):
    st.markdown(f"#### {title}")

    rows = [
        ("總報酬", f"{perf['total_return']:.2%}", "年化報酬", f"{perf['ann_return']:.2%}"),
        ("最大回撤", f"{perf['max_dd']:.2%}", "Sharpe", f"{perf['sharpe']:.2f}"),
        ("交易筆數", f"{perf['trade_count']}", "勝率", f"{perf['win_rate']:.2%}"),
        ("進場次數", f"{perf['entry_count']}", "出場次數", f"{perf['exit_count']}"),
        ("平均單筆報酬", f"{perf['avg_trade_return']:.2%}", "最佳單筆", f"{perf['best_trade']:.2%}"),
        ("最差單筆", f"{perf['worst_trade']:.2%}", "平均持有 bars", f"{perf['avg_holding_bars']:.1f}"),
    ]

    for left_label, left_value, right_label, right_value in rows:
        c1, c2 = st.columns(2)
        with c1:
            st.metric(left_label, left_value)
        with c2:
            st.metric(right_label, right_value)

def render_basic_perf_metrics(title: str, perf: dict):
    """
    保留一個較簡版，之後若別頁還想用簡短摘要可以用這個。
    """
    st.markdown(f"#### {title}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("總報酬", f"{perf['total_return']:.2%}")
    with c2:
        st.metric("最大回撤", f"{perf['max_dd']:.2%}")
    with c3:
        st.metric("Sharpe", f"{perf['sharpe']:.2f}")