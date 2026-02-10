#!/usr/bin/env python3
"""
Techy Pete's Dashboard Generator - Creates an interactive HTML trading dashboard.
Reads portfolio state and generates a self-contained HTML file with Chart.js visualizations.
"""

import json
import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HISTORY_FILE = DATA_DIR / "value_history.json"
DASHBOARD_FILE = DATA_DIR / "dashboard.html"


def load_json(filepath):
    """Load a JSON file, return empty dict/list on failure."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} if "portfolio" in str(filepath) else []


def generate_dashboard(signals_data=None):
    """Generate the complete HTML dashboard."""
    portfolio = load_json(PORTFOLIO_FILE)
    history = load_json(HISTORY_FILE)
    
    if not portfolio:
        print("No portfolio data found. Run the bot first.")
        return
    
    # Compute summary values
    cash = portfolio.get("cash", 0)
    starting_cash = portfolio.get("starting_cash", 10000)
    positions = portfolio.get("positions", {})
    trades = portfolio.get("trade_history", [])
    
    positions_value = sum(
        p.get("quantity", 0) * p.get("current_price", p.get("entry_price", 0))
        for p in positions.values()
    )
    total_value = cash + positions_value
    total_pnl = total_value - starting_cash
    total_return_pct = (total_pnl / starting_cash * 100) if starting_cash else 0
    
    sells = [t for t in trades if t.get("action") == "SELL"]
    wins = [t for t in sells if t.get("pnl", 0) > 0]
    win_rate = (len(wins) / len(sells) * 100) if sells else 0
    realized_pnl = sum(t.get("pnl", 0) for t in sells)
    
    # Prepare positions data for JS
    positions_js = []
    for sym, p in sorted(positions.items()):
        entry_price = p.get("entry_price", 0)
        current_price = p.get("current_price", entry_price)
        quantity = p.get("quantity", 0)
        mv = quantity * current_price
        cb = quantity * entry_price
        pnl = mv - cb
        pnl_pct = (pnl / cb * 100) if cb else 0
        positions_js.append({
            "symbol": sym,
            "type": p.get("asset_type", "stock"),
            "quantity": round(quantity, 4),
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "market_value": round(mv, 2),
            "cost_basis": round(cb, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "entry_date": p.get("entry_date", "")[:10],
        })
    
    # Prepare trades data for JS
    trades_js = []
    for t in reversed(trades[-100:]):  # Last 100 trades, newest first
        trades_js.append({
            "timestamp": t.get("timestamp", "")[:19].replace("T", " "),
            "action": t.get("action", ""),
            "symbol": t.get("symbol", ""),
            "quantity": round(t.get("quantity", 0), 4),
            "price": round(t.get("price", 0), 2),
            "total": round(t.get("total", 0), 2),
            "pnl": round(t.get("pnl", 0), 2) if "pnl" in t else None,
            "reason": t.get("reason", "")[:80],
        })
    
    # Prepare history for equity curve
    history_js = []
    for h in history:
        history_js.append({
            "timestamp": h.get("timestamp", ""),
            "value": round(h.get("total_value", starting_cash), 2),
            "cash": round(h.get("cash", 0), 2),
        })
    
    # Prepare signals data
    signals_js = signals_data or []
    
    # Asset allocation
    allocation = {}
    for p in positions_js:
        atype = p["type"]
        allocation[atype] = allocation.get(atype, 0) + p["market_value"]
    allocation["cash"] = cash
    
    last_updated = portfolio.get("last_updated", datetime.datetime.now().isoformat())
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Techy Pete's Investment App</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0"></script>
    <style>
        :root {{
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --bg-card-hover: #1c2333;
            --border: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #484f58;
            --accent: #58a6ff;
            --accent-dim: #1f6feb;
            --green: #3fb950;
            --green-dim: #238636;
            --red: #f85149;
            --red-dim: #da3633;
            --yellow: #d29922;
            --purple: #bc8cff;
            --cyan: #39d2c0;
            --orange: #f0883e;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            line-height: 1.5;
            min-height: 100vh;
        }}
        
        .dashboard {{
            max-width: 1440px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Header */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 28px;
            background: linear-gradient(135deg, #161b22 0%, #1a2332 100%);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .logo {{
            font-size: 28px;
            font-weight: 800;
            letter-spacing: 2px;
            background: linear-gradient(135deg, var(--cyan) 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .logo-sub {{
            font-size: 12px;
            color: var(--text-secondary);
            letter-spacing: 3px;
            text-transform: uppercase;
        }}
        
        .header-right {{
            text-align: right;
        }}
        
        .last-update {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        
        .status-active {{
            background: rgba(63, 185, 80, 0.15);
            color: var(--green);
            border: 1px solid rgba(63, 185, 80, 0.3);
        }}
        
        /* KPI Row */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 24px;
            transition: border-color 0.2s;
        }}
        
        .kpi-card:hover {{
            border-color: var(--accent-dim);
        }}
        
        .kpi-label {{
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }}
        
        .kpi-value {{
            font-size: 30px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 4px;
            font-variant-numeric: tabular-nums;
        }}
        
        .kpi-change {{
            font-size: 13px;
            font-weight: 600;
        }}
        
        .positive {{ color: var(--green); }}
        .negative {{ color: var(--red); }}
        .neutral {{ color: var(--text-secondary); }}
        
        /* Chart Grid */
        .chart-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 16px;
            margin-bottom: 20px;
        }}
        
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 24px;
        }}
        
        .chart-card h3 {{
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }}
        
        .chart-card canvas {{
            max-height: 300px;
        }}
        
        .full-width {{
            grid-column: 1 / -1;
        }}
        
        /* Tables */
        .table-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 24px;
            margin-bottom: 20px;
            overflow-x: auto;
        }}
        
        .table-card h3 {{
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        thead th {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 2px solid var(--border);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}
        
        thead th:hover {{
            color: var(--text-primary);
        }}
        
        tbody td {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(48, 54, 61, 0.5);
            font-variant-numeric: tabular-nums;
        }}
        
        tbody tr:hover {{
            background: var(--bg-card-hover);
        }}
        
        .symbol-badge {{
            font-weight: 700;
            color: var(--accent);
        }}
        
        .type-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .type-stock {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
        .type-etf {{ background: rgba(188, 140, 255, 0.15); color: var(--purple); }}
        .type-crypto {{ background: rgba(57, 210, 192, 0.15); color: var(--cyan); }}
        
        .action-buy {{ color: var(--green); font-weight: 700; }}
        .action-sell {{ color: var(--red); font-weight: 700; }}
        
        /* Signals Section */
        .signals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }}
        
        .signal-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .signal-card.buy-signal {{ border-left: 3px solid var(--green); }}
        .signal-card.sell-signal {{ border-left: 3px solid var(--red); }}
        .signal-card.hold-signal {{ border-left: 3px solid var(--text-muted); }}
        
        .signal-sym {{ font-weight: 700; font-size: 15px; }}
        .signal-action {{ font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
        .signal-reasons {{ font-size: 11px; color: var(--text-secondary); margin-top: 4px; }}
        .signal-strength {{
            font-size: 22px;
            font-weight: 800;
            min-width: 50px;
            text-align: center;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 12px;
        }}
        
        /* Empty state */
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}
        
        .empty-state .icon {{ font-size: 40px; margin-bottom: 12px; }}
        
        /* Responsive */
        @media (max-width: 900px) {{
            .chart-grid {{ grid-template-columns: 1fr; }}
            .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
            .header {{ flex-direction: column; gap: 12px; }}
        }}
        
        /* Tab Navigation */
        .tab-nav {{
            display: flex;
            gap: 4px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0;
        }}
        
        .tab-btn {{
            padding: 10px 20px;
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        
        .tab-btn:hover {{ color: var(--text-primary); }}
        .tab-btn.active {{
            color: var(--accent);
            border-bottom-color: var(--accent);
        }}
        
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <!-- Header -->
        <div class="header">
            <div class="header-left">
                <div>
                    <div class="logo">TECHY PETE'S</div>
                    <div class="logo-sub">Investment App</div>
                </div>
            </div>
            <div class="header-right">
                <div class="last-update">Last Updated: {last_updated[:19].replace("T", " ")}</div>
                <div class="status-badge status-active">ACTIVE</div>
            </div>
        </div>
        
        <!-- KPIs -->
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-label">Portfolio Value</div>
                <div class="kpi-value" id="kpi-value">${total_value:,.2f}</div>
                <div class="kpi-change {'positive' if total_pnl >= 0 else 'negative'}">
                    {'&#9650;' if total_pnl >= 0 else '&#9660;'} ${abs(total_pnl):,.2f} ({total_return_pct:+.2f}%)
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Cash Available</div>
                <div class="kpi-value">${cash:,.2f}</div>
                <div class="kpi-change neutral">{cash/total_value*100:.1f}% of portfolio</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Open Positions</div>
                <div class="kpi-value">{len(positions)}</div>
                <div class="kpi-change neutral">${positions_value:,.2f} invested</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Realized P&L</div>
                <div class="kpi-value {'positive' if realized_pnl >= 0 else 'negative'}">${realized_pnl:,.2f}</div>
                <div class="kpi-change neutral">{len(sells)} closed trades</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Win Rate</div>
                <div class="kpi-value">{win_rate:.1f}%</div>
                <div class="kpi-change neutral">{len(wins)}W / {len(sells) - len(wins)}L</div>
            </div>
        </div>
        
        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('overview')">Overview</button>
            <button class="tab-btn" onclick="switchTab('positions')">Positions</button>
            <button class="tab-btn" onclick="switchTab('trades')">Trade History</button>
            <button class="tab-btn" onclick="switchTab('signals')">Bot Signals</button>
        </div>
        
        <!-- Overview Tab -->
        <div id="tab-overview" class="tab-content active">
            <div class="chart-grid">
                <div class="chart-card">
                    <h3>Equity Curve</h3>
                    <canvas id="equity-chart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Asset Allocation</h3>
                    <canvas id="allocation-chart"></canvas>
                </div>
            </div>
            <div class="chart-grid">
                <div class="chart-card full-width">
                    <h3>Position P&L</h3>
                    <canvas id="pnl-chart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Positions Tab -->
        <div id="tab-positions" class="tab-content">
            <div class="table-card">
                <h3>Open Positions ({len(positions)})</h3>
                <div id="positions-table"></div>
            </div>
        </div>
        
        <!-- Trades Tab -->
        <div id="tab-trades" class="tab-content">
            <div class="table-card">
                <h3>Trade History ({len(trades)} trades)</h3>
                <div id="trades-table"></div>
            </div>
        </div>
        
        <!-- Signals Tab -->
        <div id="tab-signals" class="tab-content">
            <div class="table-card">
                <h3>Latest Bot Signals</h3>
                <div id="signals-container"></div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            Techy Pete's Investment App &mdash; Simulated trading with real market data &mdash; Not financial advice
        </div>
    </div>
    
    <script>
        // ===== EMBEDDED DATA =====
        const POSITIONS = {json.dumps(positions_js)};
        const TRADES = {json.dumps(trades_js)};
        const HISTORY = {json.dumps(history_js)};
        const SIGNALS = {json.dumps(signals_js)};
        const ALLOCATION = {json.dumps(allocation)};
        const STARTING_CASH = {starting_cash};
        
        // ===== COLOR CONFIG =====
        const COLORS = {{
            green: '#3fb950',
            red: '#f85149',
            accent: '#58a6ff',
            cyan: '#39d2c0',
            purple: '#bc8cff',
            orange: '#f0883e',
            yellow: '#d29922',
            text: '#8b949e',
            grid: 'rgba(48, 54, 61, 0.5)',
        }};
        
        const ASSET_COLORS = {{
            stock: COLORS.accent,
            etf: COLORS.purple,
            crypto: COLORS.cyan,
            cash: COLORS.text,
        }};
        
        // ===== TAB SWITCHING =====
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            event.target.classList.add('active');
        }}
        
        // ===== CHARTS =====
        
        // Equity Curve
        function renderEquityChart() {{
            const ctx = document.getElementById('equity-chart').getContext('2d');
            
            let labels, values;
            if (HISTORY.length > 0) {{
                labels = HISTORY.map(h => h.timestamp);
                values = HISTORY.map(h => h.value);
            }} else {{
                labels = [new Date().toISOString()];
                values = [STARTING_CASH];
            }}
            
            // Add starting point if not present
            if (values.length > 0 && values[0] !== STARTING_CASH) {{
                labels.unshift(labels[0]);
                values.unshift(STARTING_CASH);
            }}
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels.map(l => new Date(l)),
                    datasets: [{{
                        label: 'Portfolio Value',
                        data: values,
                        borderColor: COLORS.cyan,
                        backgroundColor: 'rgba(57, 210, 192, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointRadius: values.length > 20 ? 0 : 3,
                        pointHoverRadius: 5,
                    }}, {{
                        label: 'Starting Capital',
                        data: values.map(() => STARTING_CASH),
                        borderColor: COLORS.text,
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        legend: {{
                            labels: {{ color: COLORS.text, usePointStyle: true, padding: 16 }}
                        }},
                        tooltip: {{
                            backgroundColor: '#1c2333',
                            borderColor: COLORS.grid,
                            borderWidth: 1,
                            titleColor: '#e6edf3',
                            bodyColor: '#e6edf3',
                            callbacks: {{
                                label: ctx => ctx.dataset.label + ': $' + ctx.parsed.y.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}})
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            type: 'time',
                            time: {{ unit: 'day', displayFormats: {{ day: 'MMM d' }} }},
                            grid: {{ color: COLORS.grid }},
                            ticks: {{ color: COLORS.text }},
                        }},
                        y: {{
                            grid: {{ color: COLORS.grid }},
                            ticks: {{
                                color: COLORS.text,
                                callback: v => '$' + v.toLocaleString()
                            }},
                        }}
                    }}
                }}
            }});
        }}
        
        // Asset Allocation Doughnut
        function renderAllocationChart() {{
            const ctx = document.getElementById('allocation-chart').getContext('2d');
            const labels = Object.keys(ALLOCATION).map(k => k.charAt(0).toUpperCase() + k.slice(1));
            const data = Object.values(ALLOCATION);
            const colors = Object.keys(ALLOCATION).map(k => {{
                const c = ASSET_COLORS[k] || COLORS.text;
                return c + 'CC';
            }});
            
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: data,
                        backgroundColor: colors,
                        borderColor: '#161b22',
                        borderWidth: 3,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ color: COLORS.text, usePointStyle: true, padding: 16 }}
                        }},
                        tooltip: {{
                            backgroundColor: '#1c2333',
                            borderColor: COLORS.grid,
                            borderWidth: 1,
                            titleColor: '#e6edf3',
                            bodyColor: '#e6edf3',
                            callbacks: {{
                                label: ctx => {{
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = ((ctx.parsed / total) * 100).toFixed(1);
                                    return ctx.label + ': $' + ctx.parsed.toLocaleString(undefined, {{minimumFractionDigits: 2}}) + ' (' + pct + '%)';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        // Position P&L Bar Chart
        function renderPnlChart() {{
            const ctx = document.getElementById('pnl-chart').getContext('2d');
            
            if (POSITIONS.length === 0) {{
                ctx.canvas.parentElement.innerHTML += '<div class="empty-state"><div class="icon">&#128200;</div><p>No open positions yet</p></div>';
                return;
            }}
            
            const sorted = [...POSITIONS].sort((a, b) => b.pnl - a.pnl);
            
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: sorted.map(p => p.symbol),
                    datasets: [{{
                        label: 'P&L ($)',
                        data: sorted.map(p => p.pnl),
                        backgroundColor: sorted.map(p => p.pnl >= 0 ? COLORS.green + 'AA' : COLORS.red + 'AA'),
                        borderColor: sorted.map(p => p.pnl >= 0 ? COLORS.green : COLORS.red),
                        borderWidth: 1,
                        borderRadius: 4,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: POSITIONS.length > 8 ? 'y' : 'x',
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: '#1c2333',
                            borderColor: COLORS.grid,
                            borderWidth: 1,
                            titleColor: '#e6edf3',
                            bodyColor: '#e6edf3',
                            callbacks: {{
                                label: ctx => {{
                                    const pos = sorted[ctx.dataIndex];
                                    return ['P&L: $' + pos.pnl.toFixed(2) + ' (' + pos.pnl_pct.toFixed(2) + '%)',
                                            'Value: $' + pos.market_value.toFixed(2)];
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{ color: COLORS.grid }},
                            ticks: {{ color: COLORS.text }},
                        }},
                        y: {{
                            grid: {{ color: COLORS.grid }},
                            ticks: {{
                                color: COLORS.text,
                                callback: v => '$' + v.toFixed(0)
                            }},
                        }}
                    }}
                }}
            }});
        }}
        
        // ===== TABLES =====
        
        function renderPositionsTable() {{
            const container = document.getElementById('positions-table');
            if (POSITIONS.length === 0) {{
                container.innerHTML = '<div class="empty-state"><div class="icon">&#128176;</div><p>No open positions. The bot will scan for opportunities on next run.</p></div>';
                return;
            }}
            
            let html = '<table><thead><tr>';
            html += '<th>Symbol</th><th>Type</th><th>Qty</th><th>Entry</th><th>Current</th><th>Value</th><th>P&L $</th><th>P&L %</th><th>Entry Date</th>';
            html += '</tr></thead><tbody>';
            
            const sorted = [...POSITIONS].sort((a, b) => b.market_value - a.market_value);
            sorted.forEach(p => {{
                const pnlClass = p.pnl >= 0 ? 'positive' : 'negative';
                const arrow = p.pnl >= 0 ? '&#9650;' : '&#9660;';
                html += '<tr>';
                html += '<td class="symbol-badge">' + p.symbol + '</td>';
                html += '<td><span class="type-badge type-' + p.type + '">' + p.type + '</span></td>';
                html += '<td>' + p.quantity + '</td>';
                html += '<td>$' + p.entry_price.toFixed(2) + '</td>';
                html += '<td>$' + p.current_price.toFixed(2) + '</td>';
                html += '<td>$' + p.market_value.toLocaleString(undefined, {{minimumFractionDigits: 2}}) + '</td>';
                html += '<td class="' + pnlClass + '">' + arrow + ' $' + Math.abs(p.pnl).toFixed(2) + '</td>';
                html += '<td class="' + pnlClass + '">' + (p.pnl_pct >= 0 ? '+' : '') + p.pnl_pct.toFixed(2) + '%</td>';
                html += '<td>' + p.entry_date + '</td>';
                html += '</tr>';
            }});
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }}
        
        function renderTradesTable() {{
            const container = document.getElementById('trades-table');
            if (TRADES.length === 0) {{
                container.innerHTML = '<div class="empty-state"><div class="icon">&#128209;</div><p>No trades yet. Run the bot to start trading.</p></div>';
                return;
            }}
            
            let html = '<table><thead><tr>';
            html += '<th>Date</th><th>Action</th><th>Symbol</th><th>Qty</th><th>Price</th><th>Total</th><th>P&L</th><th>Reason</th>';
            html += '</tr></thead><tbody>';
            
            TRADES.forEach(t => {{
                const actionClass = t.action === 'BUY' ? 'action-buy' : 'action-sell';
                const pnlStr = t.pnl !== null ? ('$' + t.pnl.toFixed(2)) : '—';
                const pnlClass = t.pnl !== null ? (t.pnl >= 0 ? 'positive' : 'negative') : '';
                html += '<tr>';
                html += '<td>' + t.timestamp + '</td>';
                html += '<td class="' + actionClass + '">' + t.action + '</td>';
                html += '<td class="symbol-badge">' + t.symbol + '</td>';
                html += '<td>' + t.quantity + '</td>';
                html += '<td>$' + t.price.toFixed(2) + '</td>';
                html += '<td>$' + t.total.toLocaleString(undefined, {{minimumFractionDigits: 2}}) + '</td>';
                html += '<td class="' + pnlClass + '">' + pnlStr + '</td>';
                html += '<td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + (t.reason || '') + '">' + (t.reason || '—') + '</td>';
                html += '</tr>';
            }});
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }}
        
        function renderSignals() {{
            const container = document.getElementById('signals-container');
            if (SIGNALS.length === 0) {{
                container.innerHTML = '<div class="empty-state"><div class="icon">&#128225;</div><p>No signals from last scan. Run the bot to generate fresh signals.</p></div>';
                return;
            }}
            
            let html = '<div class="signals-grid">';
            const sorted = [...SIGNALS].sort((a, b) => b.strength - a.strength);
            
            sorted.forEach(s => {{
                const cardClass = s.action === 'BUY' ? 'buy-signal' : s.action === 'SELL' ? 'sell-signal' : 'hold-signal';
                const actionColor = s.action === 'BUY' ? COLORS.green : s.action === 'SELL' ? COLORS.red : COLORS.text;
                html += '<div class="signal-card ' + cardClass + '">';
                html += '<div>';
                html += '<div class="signal-sym">' + s.symbol + '</div>';
                html += '<div class="signal-action" style="color:' + actionColor + '">' + s.action + '</div>';
                html += '<div class="signal-reasons">' + (s.reasons || []).slice(0, 2).join(' | ') + '</div>';
                html += '</div>';
                html += '<div class="signal-strength" style="color:' + actionColor + '">' + (s.strength || 0).toFixed(1) + '</div>';
                html += '</div>';
            }});
            
            html += '</div>';
            container.innerHTML = html;
        }}
        
        // ===== INIT =====
        renderEquityChart();
        renderAllocationChart();
        renderPnlChart();
        renderPositionsTable();
        renderTradesTable();
        renderSignals();
    </script>
</body>
</html>"""
    
    with open(DASHBOARD_FILE, "w") as f:
        f.write(html)
    
    print(f"Dashboard generated: {DASHBOARD_FILE}")
    return str(DASHBOARD_FILE)


if __name__ == "__main__":
    generate_dashboard()
