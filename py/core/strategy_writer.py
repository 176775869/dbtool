# coding=utf-8
"""
生成 Markdown 策略文件 v12.1 (修复版)
"""
from datetime import datetime, timedelta
import os, json
from trade_engine import detect_buy_signals, detect_demon_stocks

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
HISTORY_FILE = os.path.join(CONFIG_DIR, 'replay_history.json')
SCORES_FILE = os.path.join(CONFIG_DIR, 'candidate_scores.json')

def load_holdings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('current_holdings', {})
    return {}

def generate_exit_advice(holdings, main_name, main_stage, main_roles):
    lines = []
    if not holdings or all(w == 0 for w in holdings.values()):
        lines.append("- **当前空仓，无持仓需处理**")
        return lines
    mid_names = [m['name'] for m in main_roles.get('mid_cap', [])]
    lianban_name = main_roles.get('lianban_pioneer', {}).get('name', '')
    for stock, weight in holdings.items():
        if weight == 0: continue
        if stock == lianban_name:
            lines.append(f"- **{stock}（{weight}成，连板先锋）**：断板即走")
        elif stock in mid_names:
            lines.append(f"- **{stock}（{weight}成，中军）**：收盘破5日线减半，破20日线清仓")
        else:
            lines.append(f"- **{stock}（{weight}成）**：止损-5%或破5日线")
    return lines

def determine_style(roles, data):
    mid_cap = roles.get('mid_cap', [])
    lianban = roles.get('lianban_pioneer')
    mid_strong = any(m.get('pct', 0) >= 5 for m in mid_cap) if mid_cap else False
    lianban_high = lianban and lianban.get('lianban', 0) >= 3
    if mid_strong and not lianban_high:
        return "趋势主导", "优先D3低吸中军"
    elif lianban_high and not mid_strong:
        return "连板主导", "优先D2跟随先锋"
    elif mid_strong and lianban_high:
        return "趋势+连板共振", "满仓双线并行"
    return "趋势主导（默认）", "中军趋势稳健"

def generate_strategy(data, anchor, main_lines, main_msg, phase, rhythm):
    date_str = data['date']
    next_date = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    sh = data.get('sh_index', 0)
    m20 = data.get('ma20', 0)
    mlb = data.get('max_lianban', 0)

    cfg = json.load(open(CONFIG_FILE, 'r', encoding='utf-8')) if os.path.exists(CONFIG_FILE) else {}
    thr = cfg.get('environment_thresholds', {})
    if sh > m20 and total_amt > thr.get('S_amount', 22000) and mlb > thr.get('S_lianban', 5):
        env, max_cang = 'S', 4
    elif sh > m20 and total_amt >= thr.get('A_amount', 15000):
        env, max_cang = 'A', 3
    else:
        env, max_cang = 'B', 2

    holdings = load_holdings()
    current_main = main_lines[0] if main_lines else {}
    current_roles = current_main.get('roles', {})

    scores_history = {}
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            scores_history = json.load(f)

    lines = []
    lines.append(f"# 豆包模式 · 自动盘前策略（{date_str} -> {next_date}）")
    lines.append(f"> 环境：{env}级 | 仓位上限：仓{max_cang} | 阶段：{phase} | 节奏：{rhythm}")
    lines.append(f"> 铁律：情绪锚点、周期阶段、主线、角色必须定位清楚，否则不交易")
    lines.append("\n## 1. 大盘状态")
    lines.append(f"- 上证：{sh:.2f}（{data.get('sh_pct', 0):+.2f}%），成交{data.get('sh_amount', 0):.0f}亿")
    lines.append(f"- 两市成交：{total_amt:.0f}亿 | 涨跌：{data.get('up_count', 0)}/{data.get('down_count', 0)}")
    lines.append(f"- 20日线：{m20:.2f}")

    lines.append("\n## 2. 情绪周期")
    lines.append(f"- 涨停{data.get('limit_total', 0)} | 跌停{data.get('dieting_total', 0)} | 炸板{data.get('zhaban_total', 0)} | 高标{mlb}板")

    lines.append("\n## 3. 持仓处理")
    lines.extend(generate_exit_advice(holdings, current_main.get('name'), current_main.get('stage'), current_roles))

    lines.append("\n## 4. 主线评估与候选池")
    lines.append(main_msg)
    if main_lines:
        lines.append("\n| 方向 | 类型 | 阶段 | 评分 | 承载力 | 风格 | 中军 | 先锋 |")
        lines.append("|------|------|------|------|--------|------|------|------|")
        for ml in main_lines:
            roles = ml.get('roles', {})
            mid = roles.get('mid_cap', [])
            mid_names = ', '.join([m['name'] for m in mid[:2]]) if mid else '—'
            pioneer = roles.get('lianban_pioneer', {})
            pioneer_name = pioneer['name'] if pioneer else '—'
            style, _ = determine_style(roles, data)
            lines.append(f"| {ml['name']} | {ml.get('type', '-')} | {ml['stage']} | {ml['score']} | {ml.get('capacity', 0):.0%} | {style} | {mid_names} | {pioneer_name} |")

        for ml in main_lines:
            hist = scores_history.get(ml['name'], [])
            if hist:
                trail = " → ".join([f"{h['date'][-4:]}({h['score']})" for h in hist[-5:]])
                lines.append(f"\n**{ml['name']}** 评分轨迹：{trail}")
    else:
        lines.append("\n无候选方向，继续空仓。")

    # 妖股模式
    demons = detect_demon_stocks(data, anchor)
    if demons:
        lines.append("\n## 妖股观察（主跌期轻仓博弈）")
        for d in demons:
            lines.append(f"- {d['name']}({d['code']}) {d['lianban']}板 | {d['cangwei']} | 断板即走")

    # 执行清单（修复：主升期已上车则不买其他）
    buy_signals = detect_buy_signals(main_lines, data, anchor)
    lines.append("\n## 5. 明日执行清单")
    lines.append(f"- 总仓位上限：{max_cang * 10}%")
    if not buy_signals:
        lines.append("\n**执行清单为空**（条件不满足，继续观察）")
    else:
        for sig in buy_signals:
            lines.append(f"\n### {sig['name']}（{sig['type']}买点）")
            lines.append(f"- 仓位：**{sig['cangwei']}**")
            lines.append(f"- 标的：{', '.join(sig['stocks'])}")
            lines.append(f"- 条件：{sig['condition']}")
            if sig.get('timing'):
                lines.append(f"- 时间：{sig['timing']}")

    lines.append("\n---")
    lines.append("*本策略由豆包模式自动生成 v12.1*")
    return '\n'.join(lines)