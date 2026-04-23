import html
import json
import pandas as pd

from ui.strategy_lab_charts import plot_dual_trade_charts, plot_equity_compare


def _fmt_pct(x) -> str:
    try:
        return f"{float(x):.2%}"
    except Exception:
        return "-"


def _fmt_num(x, digits: int = 2) -> str:
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "-"


def _safe_str(x) -> str:
    if pd.isna(x):
        return "-"
    return str(x)


def _perf_summary_table_html(title: str, perf: dict) -> str:
    rows = [
        ("總報酬", _fmt_pct(perf.get("total_return", 0.0))),
        ("年化報酬", _fmt_pct(perf.get("ann_return", 0.0))),
        ("年化波動", _fmt_pct(perf.get("ann_vol", 0.0))),
        ("最大回撤", _fmt_pct(perf.get("max_dd", 0.0))),
        ("Sharpe", _fmt_num(perf.get("sharpe", 0.0), 2)),
        ("交易筆數", _safe_str(perf.get("trade_count", 0))),
        ("進場次數", _safe_str(perf.get("entry_count", 0))),
        ("出場次數", _safe_str(perf.get("exit_count", 0))),
        ("勝率", _fmt_pct(perf.get("win_rate", 0.0))),
        ("平均單筆報酬", _fmt_pct(perf.get("avg_trade_return", 0.0))),
        ("最佳單筆", _fmt_pct(perf.get("best_trade", 0.0))),
        ("最差單筆", _fmt_pct(perf.get("worst_trade", 0.0))),
        ("平均持有 bars", _fmt_num(perf.get("avg_holding_bars", 0.0), 1)),
    ]

    trs = "\n".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
        for k, v in rows
    )

    return f"""
    <div class="card">
      <h2>{html.escape(title)}</h2>
      <table class="metric-table">
        <tbody>
          {trs}
        </tbody>
      </table>
    </div>
    """


def _reason_counts_html(eng_df: pd.DataFrame) -> str:
    if eng_df is None or eng_df.empty or "engine_reason" not in eng_df.columns:
        return """
        <div class="card">
          <h2>Engine 原因統計</h2>
          <p>沒有可用資料。</p>
        </div>
        """

    reason_counts = (
        eng_df["engine_reason"]
        .astype(str)
        .value_counts(dropna=False)
        .rename_axis("原因")
        .reset_index(name="次數")
    )

    rows = []
    for _, row in reason_counts.iterrows():
        rows.append(
            f"<tr><td>{html.escape(str(row['原因']))}</td><td>{html.escape(str(row['次數']))}</td></tr>"
        )

    return f"""
    <div class="card">
      <h2>Engine 原因統計</h2>
      <table class="data-table">
        <thead>
          <tr><th>原因</th><th>次數</th></tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """


def _trades_table_html(title: str, trades_df: pd.DataFrame) -> str:
    if trades_df is None or trades_df.empty:
        return f"""
        <div class="card">
          <h2>{html.escape(title)}</h2>
          <p>沒有已完成交易。</p>
        </div>
        """

    df = trades_df.copy()
    df["entry_date"] = pd.to_datetime(df["entry_date"]).dt.strftime("%Y-%m-%d")
    df["exit_date"] = pd.to_datetime(df["exit_date"]).dt.strftime("%Y-%m-%d")
    df["return_pct"] = df["return_pct"].map(_fmt_pct)
    df["entry_price"] = df["entry_price"].map(lambda x: _fmt_num(x, 2))
    df["exit_price"] = df["exit_price"].map(lambda x: _fmt_num(x, 2))
    df["holding_bars"] = df["holding_bars"].map(_safe_str)
    df["is_win"] = df["is_win"].map(lambda x: "是" if bool(x) else "否")

    use_cols = [
        "entry_date",
        "exit_date",
        "side",
        "entry_price",
        "exit_price",
        "return_pct",
        "holding_bars",
        "is_win",
    ]
    df = df[use_cols]

    header_html = "".join(f"<th>{html.escape(col)}</th>" for col in df.columns)

    body_rows = []
    for _, row in df.iterrows():
        body_rows.append(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row.tolist()) + "</tr>"
        )

    return f"""
    <div class="card">
      <h2>{html.escape(title)}</h2>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>{header_html}</tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>
    </div>
    """


def _recent_preview_html(
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series,
    eng_df: pd.DataFrame,
) -> str:
    if price_df is None or price_df.empty:
        return """
        <div class="card">
          <h2>最近訊號觀察</h2>
          <p>沒有可用資料。</p>
        </div>
        """

    preview = pd.DataFrame(index=price_df.index)
    preview["日期"] = price_df.index
    preview["收盤價"] = price_df["Close"].astype(float)
    preview["原始策略訊號"] = base_signal.reindex(price_df.index).fillna(0.0).astype(float)
    preview["Engine 後訊號"] = engine_signal.reindex(price_df.index).fillna(0.0).astype(float)
    preview["Engine 判斷"] = eng_df["engine_reason"].reindex(price_df.index).astype(str)

    if "mid_regime_name" in state_df.columns:
        preview["中期市場狀態"] = state_df["mid_regime_name"].reindex(price_df.index).astype(str)

    if "weekly_weekly_background_name" in state_df.columns:
        preview["週線背景"] = state_df["weekly_weekly_background_name"].reindex(price_df.index).astype(str)

    if "fast_event_display" in state_df.columns:
        preview["快層事件"] = state_df["fast_event_display"].reindex(price_df.index).astype(str)

    preview = preview.tail(30).copy()
    preview["日期"] = pd.to_datetime(preview["日期"]).dt.strftime("%Y-%m-%d")
    preview["收盤價"] = preview["收盤價"].map(lambda x: _fmt_num(x, 2))

    header_html = "".join(f"<th>{html.escape(col)}</th>" for col in preview.columns)

    body_rows = []
    for _, row in preview.iterrows():
        body_rows.append(
            "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row.tolist()) + "</tr>"
        )

    return f"""
    <div class="card">
      <h2>最近訊號觀察</h2>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>{header_html}</tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>
    </div>
    """


def build_strategy_lab_report_html(
    strategy_key: str,
    strictness: str,
    params: dict,
    start_date,
    end_date,
    price_df: pd.DataFrame,
    state_df: pd.DataFrame,
    eng_df: pd.DataFrame,
    base_signal: pd.Series,
    engine_signal: pd.Series,
    base_perf: dict,
    eng_perf: dict,
) -> str:
    base_fig, engine_fig = plot_dual_trade_charts(
        price_df=price_df,
        base_signal=base_signal,
        engine_signal=engine_signal,
        base_trades_df=base_perf.get("trades_df"),
        engine_trades_df=eng_perf.get("trades_df"),
        eng_df=eng_df,
    )

    equity_fig = plot_equity_compare(
        base_perf=base_perf,
        eng_perf=eng_perf,
        title="資金曲線比較",
    )

    base_chart_html = base_fig.to_html(full_html=False, include_plotlyjs="cdn")
    engine_chart_html = engine_fig.to_html(full_html=False, include_plotlyjs=False)
    equity_chart_html = equity_fig.to_html(full_html=False, include_plotlyjs=False)

    params_pretty = html.escape(json.dumps(params, ensure_ascii=False, indent=2))

    return f"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <title>Strategy Lab Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #0b1020;
      color: #f3f4f6;
      margin: 0;
      padding: 24px;
      line-height: 1.6;
    }}
    .container {{
      max-width: 1400px;
      margin: 0 auto;
    }}
    h1, h2, h3 {{
      margin-top: 0;
      color: #ffffff;
    }}
    .muted {{
      color: #cbd5e1;
      font-size: 14px;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 20px;
    }}
    .card {{
      background: #111827;
      border: 1px solid #243041;
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 20px;
      box-sizing: border-box;
    }}
    .metric-table, .data-table {{
      width: 100%;
      border-collapse: collapse;
    }}
    .metric-table th, .metric-table td,
    .data-table th, .data-table td {{
      border-bottom: 1px solid #243041;
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    .metric-table th {{
      width: 38%;
      color: #cbd5e1;
      font-weight: 600;
    }}
    .metric-table td {{
      color: #ffffff;
    }}
    .data-table th {{
      background: #172133;
      color: #e5e7eb;
      position: sticky;
      top: 0;
    }}
    .table-wrap {{
      overflow-x: auto;
      max-height: 520px;
      overflow-y: auto;
      border-radius: 8px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #0f172a;
      border: 1px solid #243041;
      border-radius: 10px;
      padding: 12px;
      overflow-x: auto;
    }}
    .section-title {{
      margin: 28px 0 12px 0;
    }}
    @media (max-width: 960px) {{
      .grid-2 {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Strategy Lab 完整互動報告</h1>
      <div class="muted">
        策略：{html.escape(strategy_key)}<br>
        Engine 強度：{html.escape(strictness)}<br>
        回測區間：{html.escape(str(start_date))} ~ {html.escape(str(end_date))}
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h2>策略設定</h2>
        <pre>{params_pretty}</pre>
      </div>
      <div class="card">
        <h2>報告用途</h2>
        <p>
          這份報告用來完整比較：原始策略與加入 Engine 後，在同一段回測期間內的
          交易行為、績效表現、Engine 介入方式，以及最近市場背景下的決策差異。
        </p>
      </div>
    </div>

    <div class="grid-2">
      {_perf_summary_table_html("原始策略完整績效", base_perf)}
      {_perf_summary_table_html("加入 Engine 後完整績效", eng_perf)}
    </div>

    <div class="card">
      <h2 class="section-title">原始策略交易圖</h2>
      {base_chart_html}
    </div>

    <div class="card">
      <h2 class="section-title">加入 Engine 後的交易圖</h2>
      {engine_chart_html}
    </div>

    <div class="card">
      <h2 class="section-title">資金曲線比較</h2>
      {equity_chart_html}
    </div>

    {_reason_counts_html(eng_df)}

    {_trades_table_html("原始策略交易明細", base_perf.get("trades_df"))}

    {_trades_table_html("加入 Engine 後交易明細", eng_perf.get("trades_df"))}

    {_recent_preview_html(
        price_df=price_df,
        state_df=state_df,
        base_signal=base_signal,
        engine_signal=engine_signal,
        eng_df=eng_df,
    )}
  </div>
</body>
</html>
"""