#!/usr/bin/env python3
"""
Techy Pete's Comparison Dashboard Generator
Generates a head-to-head HTML dashboard for 5 competing trading bots.
"""

import json
import datetime
from pathlib import Path

PLATFORM_DIR = Path(__file__).parent
BOTS_DIR = PLATFORM_DIR / "bots"
DASHBOARD_FILE = PLATFORM_DIR / "arena_dashboard.html"

BOT_IDS = ["momentum_pete", "cautious_carl", "mean_reversion_mary", "volume_victor", "yolo_yolanda"]


def load_bot_history(bot_id):
    """Load value_history.json for a bot."""
    history_file = BOTS_DIR / bot_id / "value_history.json"
    try:
        with open(history_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_bot_portfolio(bot_id):
    """Load portfolio.json for a bot."""
    portfolio_file = BOTS_DIR / bot_id / "portfolio.json"
    try:
        with open(portfolio_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def generate_comparison_dashboard(results=None, bot_roster=None):
    """Generate the comparison HTML dashboard."""
    
    # If no results passed, load from disk
    if results is None:
        results = []
        default_roster = [
            {"id": "momentum_pete", "name": "Momentum Pete", "emoji": "🚀", "color": "#58a6ff"},
            {"id": "cautious_carl", "name": "Cautious Carl", "emoji": "🛡️", "color": "#3fb950"},
            {"id": "mean_reversion_mary", "name": "Mean Reversion Mary", "emoji": "🔄", "color": "#bc8cff"},
            {"id": "volume_victor", "name": "Volume Victor", "emoji": "📊", "color": "#f0883e"},
            {"id": "yolo_yolanda", "name": "YOLO Yolanda", "emoji": "🎲", "color": "#f85149"},
        ]
        bot_roster = default_roster
        
        for bot_info in default_roster:
            bot_id = bot_info["id"]
            portfolio_data = load_bot_portfolio(bot_id)
            config_file = BOTS_DIR / bot_id / "config.json"
            config = {}
            try:
                with open(config_file) as f:
                    config = json.load(f)
            except:
                pass
            
            cash = portfolio_data.get("cash", 10000)
            starting_cash = portfolio_data.get("starting_cash", 10000)
            positions = portfolio_data.get("positions", {})
            trades = portfolio_data.get("trade_history", [])
            
            pos_value = sum(
                p.get("quantity", 0) * p.get("current_price", p.get("entry_price", 0))
                for p in positions.values()
            )
            total_value = cash + pos_value
            total_pnl = total_value - starting_cash
            total_return_pct = (total_pnl / starting_cash * 100) if starting_cash else 0
            
            sells = [t for t in trades if t.get("action") == "SELL"]
            wins = [t for t in sells if t.get("pnl", 0) > 0]
            win_rate = (len(wins) / len(sells) * 100) if sells else 0
            realized_pnl = sum(t.get("pnl", 0) for t in sells)
            
            positions_list = []
            for sym, p in sorted(positions.items()):
                ep = p.get("entry_price", 0)
                cp = p.get("current_price", ep)
                q = p.get("quantity", 0)
                mv = q * cp
                pnl = mv - (q * ep)
                positions_list.append({
                    "symbol": sym, "type": p.get("asset_type", "stock"),
                    "quantity": round(q, 4), "entry_price": round(ep, 2),
                    "current_price": round(cp, 2), "market_value": round(mv, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((pnl / (q * ep) * 100) if q * ep else 0, 2),
                })
            
            results.append({
                "bot_id": bot_id,
                "bot_name": bot_info["name"],
                "emoji": bot_info["emoji"],
                "color": bot_info["color"],
                "description": config.get("bot_description", ""),
                "summary": {
                    "total_value": round(total_value, 2),
                    "cash": round(cash, 2),
                    "positions_value": round(pos_value, 2),
                    "total_pnl": round(total_pnl, 2),
                    "total_return_pct": round(total_return_pct, 2),
                    "realized_pnl": round(realized_pnl, 2),
                    "unrealized_pnl": round(total_pnl - realized_pnl, 2),
                    "num_positions": len(positions),
                    "num_trades": len(trades),
                    "win_rate": round(win_rate, 1),
                    "positions": positions_list,
                    "starting_cash": starting_cash,
                },
                "trades_this_cycle": 0,
                "signals": [],
            })
    
    # Load equity curve histories for all bots
    histories = {}
    for bot_info in (bot_roster or []):
        histories[bot_info["id"]] = load_bot_history(bot_info["id"])
    
    # Sort results by return (leaderboard)
    ranked = sorted(results, key=lambda r: r["summary"]["total_return_pct"], reverse=True)
    
    # Build positions matrix: which bots hold which symbols
    all_symbols = set()
    for r in results:
        for p in r["summary"].get("positions", []):
            all_symbols.add(p["symbol"])
    all_symbols = sorted(all_symbols)
    
    last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare recent trades per bot (last 10 each)
    recent_trades = {}
    for r in results:
        bot_id = r["bot_id"]
        portfolio_data = load_bot_portfolio(bot_id)
        trades = portfolio_data.get("trade_history", [])
        recent = []
        for t in reversed(trades[-10:]):
            recent.append({
                "timestamp": t.get("timestamp", "")[:16].replace("T", " "),
                "action": t.get("action", ""),
                "symbol": t.get("symbol", ""),
                "quantity": round(t.get("quantity", 0), 4),
                "price": round(t.get("price", 0), 2),
                "pnl": round(t.get("pnl", 0), 2) if "pnl" in t else None,
                "reason": t.get("reason", "")[:60],
            })
        recent_trades[bot_id] = recent

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="120">
    <title>Techy Pete's 5-Bot Arena</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0"></script>
    <style>
        :root {{
            --bg-dark: #0d1117; --bg-card: #161b22; --bg-hover: #1c2333;
            --border: #30363d; --text: #e6edf3; --text-sec: #8b949e; --text-muted: #484f58;
            --green: #3fb950; --red: #f85149; --cyan: #39d2c0;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; background: var(--bg-dark); color: var(--text); line-height: 1.5; }}
        .dashboard {{ max-width: 1440px; margin: 0 auto; padding: 20px; }}

        .header {{ text-align: center; padding: 28px; background: linear-gradient(135deg, #161b22 0%, #1a2332 100%); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px; }}
        .logo {{ font-size: 32px; font-weight: 800; letter-spacing: 2px; background: linear-gradient(135deg, var(--cyan), #58a6ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        .logo-sub {{ font-size: 14px; color: var(--text-sec); letter-spacing: 3px; text-transform: uppercase; margin-top: 4px; }}
        .last-update {{ font-size: 12px; color: var(--text-muted); margin-top: 8px; }}

        .leaderboard {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }}
        .leader-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; text-align: center; position: relative; overflow: hidden; transition: transform 0.2s; }}
        .leader-card:hover {{ transform: translateY(-2px); }}
        .leader-card .rank-stripe {{ position: absolute; top: 0; left: 0; right: 0; height: 4px; }}
        .leader-card .rank {{ font-size: 28px; margin-bottom: 4px; }}
        .leader-card .bot-name {{ font-size: 14px; font-weight: 700; margin-bottom: 8px; }}
        .leader-card .bot-value {{ font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }}
        .leader-card .bot-return {{ font-size: 15px; font-weight: 700; margin: 4px 0; }}
        .leader-card .bot-stats {{ font-size: 11px; color: var(--text-sec); }}
        .positive {{ color: var(--green); }} .negative {{ color: var(--red); }}

        .chart-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 24px; }}
        .chart-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; }}
        .chart-card h3 {{ font-size: 13px; color: var(--text-sec); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
        .chart-card canvas {{ max-height: 320px; }}
        .full-width {{ grid-column: 1 / -1; }}

        .matrix-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 20px 24px; margin-bottom: 24px; overflow-x: auto; }}
        .matrix-card h3 {{ font-size: 13px; color: var(--text-sec); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        thead th {{ text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--border); color: var(--text-sec); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }}
        tbody td {{ padding: 8px 10px; border-bottom: 1px solid rgba(48,54,61,0.5); font-variant-numeric: tabular-nums; }}
        tbody tr:hover {{ background: var(--bg-hover); }}
        .symbol-badge {{ font-weight: 700; color: #58a6ff; }}
        .held {{ text-align: center; font-size: 16px; }} .not-held {{ text-align: center; color: var(--text-muted); }}

        .bots-detail {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
        .bot-detail-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
        .bot-detail-card h4 {{ font-size: 15px; margin-bottom: 4px; }}
        .bot-detail-card .desc {{ font-size: 12px; color: var(--text-sec); margin-bottom: 12px; }}
        .mini-table {{ width: 100%; font-size: 11px; }}
        .mini-table th {{ padding: 4px 6px; text-align: left; color: var(--text-sec); font-size: 10px; text-transform: uppercase; border-bottom: 1px solid var(--border); }}
        .mini-table td {{ padding: 4px 6px; border-bottom: 1px solid rgba(48,54,61,0.3); }}
        .action-buy {{ color: var(--green); font-weight: 700; }} .action-sell {{ color: var(--red); font-weight: 700; }}

        .footer {{ text-align: center; padding: 20px; color: var(--text-muted); font-size: 12px; }}

        @media (max-width: 1000px) {{ .leaderboard {{ grid-template-columns: repeat(2, 1fr); }} .chart-grid {{ grid-template-columns: 1fr; }} .bots-detail {{ grid-template-columns: 1fr; }} }}
        @media (max-width: 600px) {{ .leaderboard {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
<div class="dashboard">
    <div class="header">
        <div class="logo">TECHY PETE'S</div>
        <div class="logo-sub">5-Bot Investment Arena</div>
        <div class="last-update">Last Updated: {last_updated}</div>
    </div>

    <!-- Leaderboard -->
    <div class="leaderboard">"""

    medals = ["🥇", "🥈", "🥉", "4th", "5th"]
    for i, r in enumerate(ranked):
        s = r["summary"]
        pnl_class = "positive" if s["total_pnl"] >= 0 else "negative"
        pnl_sign = "+" if s["total_pnl"] >= 0 else ""
        html += f"""
        <div class="leader-card">
            <div class="rank-stripe" style="background:{r['color']}"></div>
            <div class="rank">{medals[i]}</div>
            <div class="bot-name" style="color:{r['color']}">{r['emoji']} {r['bot_name']}</div>
            <div class="bot-value">${s['total_value']:,.2f}</div>
            <div class="bot-return {pnl_class}">{pnl_sign}{s['total_return_pct']:.2f}%</div>
            <div class="bot-stats">{s['num_positions']} positions &middot; {s['num_trades']} trades &middot; {s['win_rate']:.0f}% win</div>
        </div>"""

    html += """
    </div>

    <!-- Charts -->
    <div class="chart-grid">
        <div class="chart-card">
            <h3>Equity Curves (Head-to-Head)</h3>
            <canvas id="equity-chart"></canvas>
        </div>
        <div class="chart-card">
            <h3>Return % Comparison</h3>
            <canvas id="return-chart"></canvas>
        </div>
    </div>"""

    # Positions Matrix
    if all_symbols:
        html += """
    <div class="matrix-card">
        <h3>Positions Matrix — Who Holds What</h3>
        <table><thead><tr><th>Symbol</th>"""
        for r in results:
            html += f'<th style="color:{r["color"]}">{r["emoji"]} {r["bot_name"].split()[0]}</th>'
        html += "</tr></thead><tbody>"

        for sym in all_symbols:
            html += f'<tr><td class="symbol-badge">{sym}</td>'
            for r in results:
                held_syms = [p["symbol"] for p in r["summary"].get("positions", [])]
                if sym in held_syms:
                    pos = next(p for p in r["summary"]["positions"] if p["symbol"] == sym)
                    pos_pnl = pos.get("pnl", pos.get("unrealized_pnl", 0))
                    pos_mv = pos.get("market_value", 0)
                    pnl_class = "positive" if pos_pnl >= 0 else "negative"
                    html += f'<td class="held {pnl_class}">${pos_mv:,.0f}</td>'
                else:
                    html += '<td class="not-held">—</td>'
            html += "</tr>"
        html += "</tbody></table></div>"

    # Bot Detail Cards
    html += '<div class="bots-detail">'
    for r in results:
        bot_id = r["bot_id"]
        trades_list = recent_trades.get(bot_id, [])
        desc = r.get("description", "")
        html += f"""
        <div class="bot-detail-card">
            <h4 style="color:{r['color']}">{r['emoji']} {r['bot_name']}</h4>
            <div class="desc">{desc}</div>"""

        if trades_list:
            html += '<table class="mini-table"><thead><tr><th>Date</th><th>Action</th><th>Symbol</th><th>Price</th><th>P&L</th><th>Reason</th></tr></thead><tbody>'
            for t in trades_list[:6]:
                ac = "action-buy" if t["action"] == "BUY" else "action-sell"
                pnl_str = f'${t["pnl"]:.2f}' if t["pnl"] is not None else "—"
                pnl_c = "positive" if (t["pnl"] or 0) >= 0 else "negative"
                html += f'<tr><td>{t["timestamp"]}</td><td class="{ac}">{t["action"]}</td><td class="symbol-badge">{t["symbol"]}</td><td>${t["price"]:.2f}</td><td class="{pnl_c}">{pnl_str}</td><td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{t["reason"]}">{t["reason"]}</td></tr>'
            html += '</tbody></table>'
        else:
            html += '<div style="color:var(--text-muted);font-size:12px;padding:12px 0">No trades yet</div>'

        html += '</div>'

    html += '</div>'

    # Footer
    html += """
    <div class="footer">
        Techy Pete's Investment App &mdash; 5-Bot Arena &mdash; Simulated trading with real market data &mdash; Not financial advice
    </div>
</div>

<script>"""

    # Embed data — build JSON strings outside the f-string to avoid brace conflicts
    results_js = json.dumps([
        {"bot_id": r["bot_id"], "bot_name": r["bot_name"], "color": r["color"],
         "emoji": r["emoji"], "total_value": r["summary"]["total_value"],
         "total_return_pct": r["summary"]["total_return_pct"],
         "total_pnl": r["summary"]["total_pnl"]}
        for r in ranked
    ])
    histories_js = json.dumps(histories)

    html += f"""
    const RESULTS = {results_js};
    const HISTORIES = {histories_js};
    const STARTING_CASH = 10000;
    """

    html += """
    // Colors
    const GRID_COLOR = 'rgba(48, 54, 61, 0.5)';
    const TEXT_COLOR = '#8b949e';

    // Equity Curves
    (function() {
        const ctx = document.getElementById('equity-chart').getContext('2d');
        const datasets = [];

        for (const r of RESULTS) {
            const hist = HISTORIES[r.bot_id] || [];
            if (hist.length === 0) {
                datasets.push({
                    label: r.emoji + ' ' + r.bot_name,
                    data: [{ x: new Date(), y: STARTING_CASH }],
                    borderColor: r.color,
                    borderWidth: 2, fill: false, tension: 0.3, pointRadius: 0, pointHoverRadius: 4,
                });
            } else {
                datasets.push({
                    label: r.emoji + ' ' + r.bot_name,
                    data: hist.map(h => ({ x: new Date(h.timestamp), y: h.total_value })),
                    borderColor: r.color,
                    borderWidth: 2, fill: false, tension: 0.3, pointRadius: hist.length > 20 ? 0 : 2, pointHoverRadius: 5,
                });
            }
        }

        // Baseline
        const allDates = [];
        for (const r of RESULTS) {
            const hist = HISTORIES[r.bot_id] || [];
            hist.forEach(h => allDates.push(new Date(h.timestamp)));
        }
        if (allDates.length > 0) {
            const minDate = new Date(Math.min(...allDates));
            const maxDate = new Date(Math.max(...allDates));
            datasets.push({
                label: 'Starting Capital',
                data: [{ x: minDate, y: STARTING_CASH }, { x: maxDate, y: STARTING_CASH }],
                borderColor: TEXT_COLOR, borderWidth: 1, borderDash: [5, 5], pointRadius: 0, fill: false,
            });
        }

        new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: TEXT_COLOR, usePointStyle: true, padding: 12, font: { size: 11 } } },
                    tooltip: {
                        backgroundColor: '#1c2333', borderColor: GRID_COLOR, borderWidth: 1,
                        titleColor: '#e6edf3', bodyColor: '#e6edf3',
                        callbacks: { label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2 }) }
                    }
                },
                scales: {
                    x: { type: 'time', time: { unit: 'day', displayFormats: { day: 'MMM d' } }, grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR } },
                    y: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR, callback: v => '$' + v.toLocaleString() } }
                }
            }
        });
    })();

    // Return % Bar Chart
    (function() {
        const ctx = document.getElementById('return-chart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: RESULTS.map(r => r.emoji + ' ' + r.bot_name.split(' ')[0]),
                datasets: [{
                    label: 'Return %',
                    data: RESULTS.map(r => r.total_return_pct),
                    backgroundColor: RESULTS.map(r => r.total_return_pct >= 0 ? r.color + 'AA' : '#f85149AA'),
                    borderColor: RESULTS.map(r => r.color),
                    borderWidth: 1, borderRadius: 4,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1c2333', borderColor: GRID_COLOR, borderWidth: 1,
                        titleColor: '#e6edf3', bodyColor: '#e6edf3',
                        callbacks: { label: ctx => { const r = RESULTS[ctx.dataIndex]; return [r.bot_name + ': ' + r.total_return_pct.toFixed(2) + '%', 'P&L: $' + r.total_pnl.toFixed(2)]; } }
                    }
                },
                scales: {
                    x: { grid: { color: GRID_COLOR }, ticks: { color: TEXT_COLOR, callback: v => v + '%' } },
                    y: { grid: { display: false }, ticks: { color: TEXT_COLOR, font: { size: 12, weight: 'bold' } } }
                }
            }
        });
    })();
    </script>
</body>
</html>"""

    with open(DASHBOARD_FILE, "w") as f:
        f.write(html)

    print(f"Arena dashboard generated: {DASHBOARD_FILE}")
    return str(DASHBOARD_FILE)


if __name__ == "__main__":
    generate_comparison_dashboard()
