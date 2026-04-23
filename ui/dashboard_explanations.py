from ui.dashboard_helpers import pretty_regime_label, pretty_weekly_label, safe_get


# =========================================================
# Parts Library
# =========================================================
VOLATILITY_PARTS = {
    "high_vol": {
        "label": "高波動",
        "headline": "波動明顯放大，市場短期擺動與不確定性都偏高。",
        "trait": "價格容易急拉急殺，節奏通常不平穩，單根 K 棒的振幅也會比較大。",
        "risk": "最容易出現追高殺低、節奏錯判，或是看對方向卻被波動洗掉。",
    },
    "compressed": {
        "label": "壓縮",
        "headline": "波動收斂，市場進入較安靜、較收縮的狀態。",
        "trait": "價格擺動幅度變小，常見於整理、蓄勢，或較安靜的趨勢延續階段。",
        "risk": "最容易被誤解成『沒行情』，但實際上壓縮常常是下一段擴張前的前奏。",
    },
    "normal": {
        "label": "正常波動",
        "headline": "波動大致落在一般範圍，市場沒有明顯過度擴張或過度收斂。",
        "trait": "價格仍會波動，但節奏相對沒那麼極端，環境介於高波動與壓縮之間。",
        "risk": "容易讓人忽略風險，因為看起來不刺激，但實際上仍然可能逐步偏向某個方向。",
    },
}

STRUCTURE_PARTS = {
    "messy": {
        "label": "混亂",
        "headline": "市場走法不整齊，方向與節奏常被反覆拉扯。",
        "trait": "即使市場有方向，過程中也容易伴隨假突破、急拉急殺、反彈或回吐。",
        "risk": "最容易出現『方向判對、節奏做錯』，或把雜訊誤當成新趨勢。",
    },
    "stable": {
        "label": "穩定",
        "headline": "市場結構相對整齊，方向延續性通常較好。",
        "trait": "價格移動比較有秩序，節奏較一致，通常比混亂結構更容易閱讀。",
        "risk": "最容易讓人過度自信，以為行情會一直很順，忽略正常回撤與節奏變化。",
    },
    "neutral": {
        "label": "中性結構",
        "headline": "市場結構沒有特別偏向穩定或混亂，介於兩者之間。",
        "trait": "它不是完全沒有方向，而是走勢乾淨度沒有明顯特色，可讀性中等。",
        "risk": "最容易被忽略，但這往往代表市場沒有你想像中那麼好讀。",
    },
}

DIRECTION_PARTS = {
    "bull_range": {
        "label": "偏多盤整",
        "headline": "市場重心偏強，但主要仍以整理為主，不是全面主升段。",
        "trait": "價格雖然不一定持續創高，但整體力量較不站在空方那邊，屬於震盪中偏強。",
        "risk": "最容易被誤當成很乾淨的多頭，結果在回檔或假突破時被洗掉。",
        "mid_bias": "中期上偏多，但比較適合等確認，而不是衝動追價。",
        "weekly_bias": "大背景對偏多較友善，但不等於任何位置都適合激進做多。",
    },
    "bear_range": {
        "label": "偏空盤整",
        "headline": "市場重心偏弱，但主要仍以整理為主，不是全面主跌段。",
        "trait": "價格雖然不一定持續創低，但整體力量較偏向弱勢一側，屬於震盪中偏弱。",
        "risk": "最容易被誤當成乾淨空頭，結果在反彈或拉回時被節奏洗掉。",
        "mid_bias": "中期上偏保守、偏防守，不適合太激進追空。",
        "weekly_bias": "大背景不站在多方，短線做多需要更高等級的證據。",
    },
    "neutral_range": {
        "label": "中性盤整",
        "headline": "市場主要在區間內整理，沒有明顯方向優勢。",
        "trait": "價格更像是在區間內反覆震盪，而不是在發展清楚的上升或下降趨勢。",
        "risk": "最容易一直預設方向，但市場本身其實還沒有選邊。",
        "mid_bias": "中期上更適合等待或輕倉，不宜過度自信。",
        "weekly_bias": "大背景偏中性，應把重點放在等待更清楚的中期與短線證據。",
    },
    "bull_bias": {
        "label": "偏多",
        "headline": "市場整體重心偏強，多方略占優勢。",
        "trait": "這不一定代表已進入高速主升段，但至少大方向不是偏弱的。",
        "risk": "最容易把『偏多』誤解成『一定大漲』，忽略整理與回撤。",
        "mid_bias": "中期上較友善於順勢偏多，但仍要分辨節奏是否乾淨。",
        "weekly_bias": "大背景較支持偏多思維，逆勢做空需要更強理由。",
    },
    "bear_bias": {
        "label": "偏空",
        "headline": "市場整體重心偏弱，空方略占優勢。",
        "trait": "這不一定代表已進入高速主跌段，但至少市場力量不是站在多方那邊。",
        "risk": "最容易把『偏空』誤解成『一定一路跌』，忽略反彈與結構噪音。",
        "mid_bias": "中期上應偏防守，若要做多要更重視短線證據。",
        "weekly_bias": "大背景偏弱，短線反彈不等於背景翻多。",
    },
    "sharp_rise": {
        "label": "急漲",
        "headline": "市場上行速度偏快，價格在較短時間內明顯向上推進。",
        "trait": "這通常比緩漲更有爆發感，也更容易伴隨情緒與動能放大。",
        "risk": "最容易過度追價，或把短線過熱當成穩定趨勢。",
        "mid_bias": "中期上偏強，但更需要注意是否過熱與追價風險。",
        "weekly_bias": "若出現在週線背景，通常代表大方向力量不弱，但不宜忽略過熱風險。",
    },
    "sharp_fall": {
        "label": "急跌",
        "headline": "市場下行速度偏快，價格在較短時間內明顯向下推進。",
        "trait": "這通常比緩跌更有殺傷力，也更容易伴隨情緒性賣壓。",
        "risk": "最容易恐慌追空，或忽略短線超跌反彈風險。",
        "mid_bias": "中期上偏弱，但不能把急跌直接等同於最佳追空點。",
        "weekly_bias": "若出現在週線背景，通常代表大方向壓力不小，但也要提防超跌後修正。",
    },
    "gradual_rise": {
        "label": "緩漲",
        "headline": "市場整體偏強，但上行節奏相對平穩。",
        "trait": "這不是爆發式急漲，而是較溫和、較持續的向上推進。",
        "risk": "最容易因為『不刺激』而低估其延續性。",
        "mid_bias": "中期上通常比急漲更好跟隨，但仍需區分是穩定還是混亂。",
        "weekly_bias": "若出現在週線背景，通常代表較成熟、較安靜的偏多底色。",
    },
    "gradual_fall": {
        "label": "緩跌",
        "headline": "市場整體偏弱，但下行節奏相對平穩。",
        "trait": "這不是崩跌式急殺，而是較慢、較持續的走弱。",
        "risk": "最容易低估其持續性，因為它看起來不夠劇烈。",
        "mid_bias": "中期上偏防守，真正的風險常是慢慢壓、慢慢弱。",
        "weekly_bias": "若出現在週線背景，通常代表偏弱底色具有延續性，不利激進抄底。",
    },
}

FAST_EVENT_PARTS = {
    "無事件": {
        "headline": "目前沒有額外短期事件干擾，短線警報層相對平靜。",
        "market_trait": (
            "這不代表市場一定安全，而是代表系統目前沒有看到足以被歸類為"
            "事件警報的明顯異常變化。"
        ),
        "risk_focus": (
            "最容易犯的錯，是把『無事件』誤解成『可隨便進場』。"
            "實際上，無事件只代表沒有新增異常，主背景仍然更重要。"
        ),
        "trading_bias": (
            "操作含義上，當快層無事件時，可以更依賴 mid 與 weekly 的背景判讀，"
            "而不是過度放大短線雜訊。"
        ),
    },
    "Volatility Shock（波動衝擊）": {
        "headline": "市場最近出現短期波動衝擊，代表短線不穩定性明顯升高。",
        "market_trait": (
            "價格擺動幅度突然變大，市場節奏比平常更亂，常見於消息、情緒或風險突然放大。"
        ),
        "risk_focus": (
            "最容易出現節奏錯判、進場後馬上被大波動洗掉，或把異常波動當成正常環境。"
        ),
        "trading_bias": (
            "操作含義上應更保守，降低對既有節奏的信任，必要時減倉或等待波動回穩。"
        ),
    },
    "Structural Break（結構破壞）": {
        "headline": "市場最近出現結構破壞，代表原本的走勢節奏可能正在失效。",
        "market_trait": (
            "這不是一般波動，而是原本有效的結構、節奏、型態或區間邏輯正在被打破。"
        ),
        "risk_focus": (
            "最容易犯的錯，是仍用舊結構去理解新市場，導致在失效的框架裡持續做錯。"
        ),
        "trading_bias": (
            "操作含義上應降低對原本背景與節奏的信任，先重新確認市場是否已經切換狀態。"
        ),
    },
    "Upward Burst（向上爆發）": {
        "headline": "市場最近出現短期向上爆發，代表買方力量在短時間內快速增強。",
        "market_trait": (
            "價格短期向上加速，通常帶有動能與情緒放大的特徵，但不一定等於長週期翻多。"
        ),
        "risk_focus": (
            "最容易把短線爆發誤當成完整背景翻多，進而忽略它可能只是事件型推進。"
        ),
        "trading_bias": (
            "操作含義上，這比較像短線推進力訊號，而不是單獨的大方向結論。"
            "應搭配 mid / weekly 一起看。"
        ),
    },
    "Downward Burst（向下爆發）": {
        "headline": "市場最近出現短期向下爆發，代表賣方力量在短時間內快速增強。",
        "market_trait": (
            "價格短期向下加速，通常帶有壓力釋放與情緒放大的特徵，但不一定等於長週期翻空。"
        ),
        "risk_focus": (
            "最容易把短線爆發誤當成完整背景翻空，進而忽略它可能只是事件型下壓。"
        ),
        "trading_bias": (
            "操作含義上，這比較像短線壓力訊號，而不是單獨的大方向結論。"
            "應搭配 mid / weekly 一起看。"
        ),
    },
}


# =========================================================
# Parsers
# =========================================================
def _pick_volatility_key(text: str) -> str:
    if "高波動" in text:
        return "high_vol"
    if "壓縮" in text:
        return "compressed"
    return "normal"


def _pick_structure_key(text: str) -> str:
    if "混亂" in text:
        return "messy"
    if "穩定" in text:
        return "stable"
    return "neutral"


def _pick_direction_key(text: str) -> str:
    if "偏多盤整" in text:
        return "bull_range"
    if "偏空盤整" in text:
        return "bear_range"
    if "中性盤整" in text or text == "盤整":
        return "neutral_range"
    if "偏多" in text:
        return "bull_bias"
    if "偏空" in text:
        return "bear_bias"
    if "急漲" in text:
        return "sharp_rise"
    if "急跌" in text:
        return "sharp_fall"
    if "緩漲" in text:
        return "gradual_rise"
    if "緩跌" in text:
        return "gradual_fall"
    return "neutral_range"


# =========================================================
# Builders
# =========================================================
def build_mid_explanation_bundle(regime_name: str) -> dict:
    text = str(regime_name)

    if text in ["N/A", "nan", "None", "-", ""]:
        return {
            "headline": "目前這個中期狀態尚未有足夠資訊，不建議做方向性解讀。",
            "market_trait": "這通常代表資料不足、分類尚未成熟，或目前這一層狀態不適合直接拿來判斷市場。",
            "risk_focus": "最容易犯的錯，是在沒有足夠狀態資訊時仍硬要給市場下結論。",
            "trading_bias": "操作含義上應降低主觀性，回到價格本身與其他層級證據。",
            "volatility_title": "N/A",
            "volatility_desc": "目前沒有可用的波動解讀。",
            "structure_title": "N/A",
            "structure_desc": "目前沒有可用的結構解讀。",
            "direction_title": "N/A",
            "direction_desc": "目前沒有可用的方向解讀。",
        }

    vol_key = _pick_volatility_key(text)
    struct_key = _pick_structure_key(text)
    dir_key = _pick_direction_key(text)

    vol = VOLATILITY_PARTS[vol_key]
    struct = STRUCTURE_PARTS[struct_key]
    direc = DIRECTION_PARTS[dir_key]

    headline = (
        f"目前市場屬於「{vol['label']}、{struct['label']}、{direc['label']}」的中期狀態。"
    )

    market_trait = (
        f"從市場特徵來看，{vol['trait']}"
        f"{struct['trait']}"
        f"{direc['trait']}"
    )

    risk_focus = (
        f"使用者最該注意的是：{vol['risk']}"
        f"{struct['risk']}"
        f"{direc['risk']}"
    )

    trading_bias = direc["mid_bias"]

    return {
        "headline": headline,
        "market_trait": market_trait,
        "risk_focus": risk_focus,
        "trading_bias": trading_bias,
        "volatility_title": vol["label"],
        "volatility_desc": vol["trait"],
        "structure_title": struct["label"],
        "structure_desc": struct["trait"],
        "direction_title": direc["label"],
        "direction_desc": direc["trait"],
    }


def build_weekly_background_explanation_bundle(weekly_bg_name: str) -> dict:
    text = str(weekly_bg_name)

    if "暖機" in text:
        return {
            "headline": "週線背景仍在暖機，代表高時間尺度的背景判讀尚未成熟。",
            "market_trait": (
                "這通常表示週線分類所需特徵還不完整，因此現在不能把它當成"
                "偏多、偏空或盤整背景來過度解讀。"
            ),
            "risk_focus": (
                "最容易犯的錯，是把暖機中的背景當成正式週線結論。"
                "實際上，這時候應降低對週線背景的信任程度。"
            ),
            "trading_bias": (
                "操作含義上，這時候應更依賴中期主狀態與短線證據，"
                "而不是過度倚賴週線背景。"
            ),
        }

    vol_key = _pick_volatility_key(text)
    struct_key = _pick_structure_key(text)
    dir_key = _pick_direction_key(text)

    vol = VOLATILITY_PARTS[vol_key]
    struct = STRUCTURE_PARTS[struct_key]
    direc = DIRECTION_PARTS[dir_key]

    headline = (
        f"週線背景目前屬於「{vol['label']}、{struct['label']}、{direc['label']}」的高時間尺度底色。"
    )

    market_trait = (
        f"這代表更高時間尺度下，{direc['trait']}"
        f"同時整體波動特徵偏向「{vol['label']}」，結構特徵偏向「{struct['label']}」。"
    )

    risk_focus = (
        f"使用者最該注意的是：{direc['risk']}"
        f"週線背景不是短線進出場訊號，而是用來限制你不該太自信做什麼。"
    )

    trading_bias = direc["weekly_bias"]

    return {
        "headline": headline,
        "market_trait": market_trait,
        "risk_focus": risk_focus,
        "trading_bias": trading_bias,
    }


def build_fast_explanation_bundle(fast_event_name: str) -> dict:
    text = str(fast_event_name)

    if text in FAST_EVENT_PARTS:
        return FAST_EVENT_PARTS[text]

    return {
        "headline": "目前系統偵測到一種快層事件，代表短期節奏可能出現了需要留意的變化。",
        "market_trait": (
            "快層事件不是市場大方向本身，而是短線警報層，"
            "用來提醒最近的波動、節奏、結構或動能可能和一般狀態不同。"
        ),
        "risk_focus": (
            "最容易犯的錯，是把快層事件直接當成完整方向結論。"
            "實際上，它更像短線異常提醒。"
        ),
        "trading_bias": (
            "操作含義上，應把快層事件當成執行層面的輔助判斷，"
            "而不是脫離 mid / weekly 單獨使用。"
        ),
    }


# =========================================================
# Compatibility
# =========================================================
def build_regime_explanation_bundle(regime_name: str) -> dict:
    """
    相容舊 page 呼叫。
    預設把它當成 mid regime 來解釋。
    """
    return build_mid_explanation_bundle(regime_name)


def build_market_conclusion(latest) -> str:
    mid_name = pretty_regime_label(safe_get(latest, "mid_regime_name"))
    weekly_bg_raw = safe_get(latest, "weekly_weekly_background_name")
    weekly_bg = pretty_weekly_label(weekly_bg_raw)
    fast_event = pretty_regime_label(safe_get(latest, "fast_event_display"))

    return (
        f"目前市場的中期主狀態（Mid-term Core）為「{mid_name}」。"
        f"週線背景（Weekly Background）為「{weekly_bg}」。"
        f"短期事件（Fast Event）為「{fast_event}」。"
    )