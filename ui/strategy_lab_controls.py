import streamlit as st


# =========================================================
# Strategy metadata
# =========================================================
STRATEGY_META = {
    "trend_breakout": {
        "label": "Trend Breakout（趨勢突破）",
        "short_intro": "順勢型策略。當價格有效突破區間後，假設市場可能進入新的方向延伸段。",
        "intro": (
            "這是一種順勢型策略。它不是在低點猜反彈，也不是在高點猜回落，"
            "而是在市場已經顯示出方向性之後，順著那個方向進場。"
            "它研究的重點不是『便不便宜』，而是『市場是不是已經開始發動』。"
        ),
        "research_goal": (
            "這個策略主要研究：當市場離開整理區、開始表態時，"
            "後面是否真的有機會延續，而不是很快又回到原本區間。"
        ),
        "opportunity_type": (
            "它想抓的是『方向確認後的延伸段』。"
            "也就是說，這個策略比較在意市場是否正在形成趨勢，而不是市場是否過熱或過冷。"
        ),
        "what_it_fears": (
            "它最怕的是假突破、混亂震盪、沒有方向優勢卻只是短暫刺穿區間。"
            "如果市場只是看起來突破，但其實沒有延續性，這種策略很容易被洗掉。"
        ),
        "engine_role": (
            "在這個策略裡，Engine 的角色不是幫你創造突破，而是幫你判斷："
            "這個突破是否出現在一個相對合理的市場背景裡。"
            "它主要做三件事：過濾掉背景不支持的突破、在背景轉弱時降低持倉品質、"
            "以及把不同背景下的持倉強弱區分開來。"
        ),
        "logic": [
            "做多：價格向上突破近期重要區間高點",
            "做空：價格向下跌破近期重要區間低點",
            "出場：價格回到退出區間，或原本突破結構失效",
        ],
        "strictness": {
            "low": (
                "Low 代表較低干預。Engine 會保留較多原始突破訊號，"
                "只排除背景明顯不支持的情況。"
            ),
            "medium": (
                "Medium 代表中等干預。Engine 會開始更明確地檢查日線結構、"
                "週線背景與短期事件，讓保留下來的訊號更乾淨。"
            ),
            "high": (
                "High 代表較高干預。Engine 只保留背景一致性更高的突破，"
                "因此訊號通常更少，但背景要求也更完整。"
            ),
        },
    },
    "trend_pullback": {
        "label": "Trend Pullback（趨勢回踩）",
        "short_intro": "順勢型策略。不是追突破，而是等趨勢中的回踩結束後再順著原方向進場。",
        "intro": (
            "這也是順勢型策略，但和突破不同，它不想追在價格最亢奮的時候，"
            "而是想等市場先回踩、整理、測試支撐或壓力後，再重新跟回原本方向。"
            "它研究的重點不是『市場有沒有剛開始發動』，而是『原本的方向在回踩後有沒有重新站穩』。"
        ),
        "research_goal": (
            "這個策略主要研究：當市場原本有方向後，途中出現整理或回踩時，"
            "那些回踩是否屬於健康修正，而不是趨勢結束前的最後掙扎。"
        ),
        "opportunity_type": (
            "它想抓的是『趨勢中的第二次上車機會』。"
            "也就是說，它比突破更在意背景本來就要乾淨，因為回踩策略的前提是："
            "原本的方向本來就值得信。"
        ),
        "what_it_fears": (
            "它最怕的是背景其實並不乾淨，或是表面像回踩，實際上已經進入混亂震盪。"
            "如果市場根本沒有穩定趨勢，那很多所謂的 pullback，其實只是噪音中的來回波動。"
        ),
        "engine_role": (
            "在這個策略裡，Engine 的角色比 breakout 更偏向『背景驗證器』。"
            "它不是在找回踩點，而是在判斷：這次回踩發生的市場結構，"
            "是否仍然屬於值得順勢的背景。"
        ),
        "logic": [
            "做多：上升背景中，價格回踩後重新站穩並再度轉強",
            "做空：下降背景中，價格反彈後重新轉弱並再度下行",
            "出場：回踩結構失效，或價格回到不再有利於順勢的位置",
        ],
        "strictness": {
            "low": (
                "Low 代表較低干預。Engine 會保留較多回踩訊號，"
                "只在背景明顯不合理時才做阻擋。"
            ),
            "medium": (
                "Medium 代表中等干預。Engine 會更重視原始趨勢背景是否乾淨、"
                "是否仍然一致，以及回踩後的延續性是否值得相信。"
            ),
            "high": (
                "High 代表較高干預。Engine 會要求更完整的背景一致性，"
                "因此只保留更少、但背景條件更完整的順勢回踩。"
            ),
        },
    },
}


# =========================================================
# Labels
# =========================================================
def strictness_label(s: str) -> str:
    mapping = {
        "low": "Low（低干預 / 較寬鬆）",
        "medium": "Medium（中干預 / 平衡）",
        "high": "High（高干預 / 較嚴格）",
    }
    return mapping.get(s, s)


# =========================================================
# Render
# =========================================================
def render_strategy_lab_controls():
    strategy_key = st.selectbox(
        "策略選擇",
        options=["trend_breakout", "trend_pullback"],
        format_func=lambda x: STRATEGY_META[x]["label"],
    )

    strictness = st.selectbox(
        "Engine 干預強度",
        options=["low", "medium", "high"],
        format_func=strictness_label,
        index=1,
    )

    meta = STRATEGY_META[strategy_key]

    st.markdown(f"### {meta['label']}")
    st.write(meta["short_intro"])

    st.info(meta["strictness"][strictness])

    with st.expander("這個策略在做什麼？", expanded=True):
        st.write(meta["intro"])

        st.markdown("**它主要在研究什麼**")
        st.write(meta["research_goal"])

        st.markdown("**它想抓哪一類市場機會**")
        st.write(meta["opportunity_type"])

        st.markdown("**它最怕什麼**")
        st.write(meta["what_it_fears"])

    with st.expander("Engine 在這個策略中扮演什麼角色？", expanded=False):
        st.write(meta["engine_role"])

    with st.expander("策略核心邏輯", expanded=False):
        for item in meta["logic"]:
            st.write(f"- {item}")

    with st.expander("Low / Medium / High 的中性定義", expanded=False):
        st.markdown("**Low（低干預 / 較寬鬆）**")
        st.write(meta["strictness"]["low"])

        st.markdown("**Medium（中干預 / 平衡）**")
        st.write(meta["strictness"]["medium"])

        st.markdown("**High（高干預 / 較嚴格）**")
        st.write(meta["strictness"]["high"])

    with st.expander("這頁應該怎麼看？", expanded=False):
        st.markdown(
            """
這頁不是在直接告訴你哪個版本一定最好，而是在讓你研究同一個策略在不同 Engine 干預強度下，會出現哪些差異。

你可以從四個角度看：

1. 原始訊號和 Engine 過濾後的訊號差多少  
2. 績效曲線在不同干預下怎麼改變  
3. Engine 主要是擋掉哪些訊號、保留哪些訊號  
4. 這個策略本身和這種市場背景，到底是相容還是不相容  

所以這頁的重點不是只看誰賺得最多，而是理解：
- 這個策略在什麼背景下表現較自然
- Engine 是在幫忙，還是過度干預
"""
        )

    # =========================================================
    # Strategy params
    # 要和 ui/strategy_lab_runners.py / strategies/*.py 的正式函式簽名一致
    # =========================================================
    if strategy_key == "trend_breakout":
        params = {
            "entry_window": 20,
            "trend_ma_window": 50,
            "use_trend_filter": True,
            "swing_window": 2,
        }

    elif strategy_key == "trend_pullback":
        params = {
            "trend_ma_window": 20,
            "pullback_ma_window": 10,
            "pullback_lookback": 8,
            "confirm_window": 3,
            "touch_buffer": 0.003,
            "swing_window": 1,
        }

    else:
        params = {}

    return strategy_key, strictness, params, meta