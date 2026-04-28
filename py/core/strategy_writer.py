# coding=utf-8
"""
生成 Markdown 策略文件 v11.0（双锚点 + 历史记录 + 评分轨迹）
"""
from datetime import datetime, timedelta
import os, json
from trade_engine import detect_buy_signals

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
HISTORY_FILE = os.path.join(CONFIG_DIR, 'replay_history.json')
SCORES_FILE = os.path.join(CONFIG_DIR, 'candidate_scores.json')

# ==================== 持仓管理 ====================
def load_holdings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            return cfg.get('current_holdings', {})
    return {}

def save_holdings(holdings):
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    cfg['current_holdings'] = holdings
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ==================== 卖出/止损 ====================
def generate_exit_advice(holdings, main_name, main_stage, main_roles):
    lines = []
    if not holdings or all(w == 0 for w in holdings.values()):
        lines.append("- **当前空仓，无持仓需处理**")
        return lines

    mid_cap_names = [m['name'] for m in main_roles.get('mid_cap', [])]
    lianban_name = main_roles.get('lianban_pioneer', {}).get('name', '')
    elastic_name = main_roles.get('elastic_pioneer', {}).get('name', '')

    for stock, weight in holdings.items():
        if weight == 0:
            continue
        is_lianban = (stock == lianban_name) or (stock == elastic_name)
        is_mid_cap = (stock in mid_cap_names)

        if isinstance(weight, (int, float)) and weight >= 4 and main_stage == 'E':
            lines.append(f"- **强制清仓 {stock}（{weight}成）**：主线已退潮（E），立即清仓")
        elif is_lianban:
            lines.append(f"- **{stock}（{weight}成，连板/弹性先锋）**：断板即走，不格局。开盘15分钟内若不封板则清仓")
        elif is_mid_cap:
            if main_stage == 'E':
                lines.append(f"- **{stock}（{weight}成，中军）**：主线退潮，清仓")
            elif 'D' in main_stage:
                lines.append(f"- **{stock}（{weight}成，中军）**：分歧期，收盘破5日线减半，破20日线清仓")
            else:
                lines.append(f"- **{stock}（{weight}成，中军）**：沿5日线持有，收盘破5日线减半，破20日线清仓")
        else:
            lines.append(f"- **{stock}（{weight}成）**：止损设-5%或破5日线，具体根据角色调整")
    return lines

# ==================== 风格判定 ====================
def determine_style(roles, data):
    mid_cap = roles.get('mid_cap', [])
    lianban = roles.get('lianban_pioneer')
    mid_strong = any(m.get('pct', 0) >= 5 for m in mid_cap) if mid_cap else False
    lianban_high = lianban and lianban.get('lianban', 0) >= 3
    if mid_strong and not lianban_high:
        return "趋势主导", "中军走强（涨>5%），优先D3低吸中军，其次D2跟随先锋"
    elif lianban_high and not mid_strong:
        return "连板主导", "连板高度突出（≥3板），优先D2跟随先锋，轻仓趋势中军"
    elif mid_strong and lianban_high:
        return "趋势+连板共振", "中军和先锋同步走强，满仓操作，双线并行"
    else:
        return "趋势主导（默认）", "中军趋势稳健，优先低吸中军，等待先锋弱转强"

# ==================== 历史记录 ====================
def save_replay_history(anchor, data, main_lines, env):
    today = data['date']
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)

    primary = anchor.get('primary_anchor') or {}
    challenger = anchor.get('challenger_anchor') or {}

    entry = {
        "date": today,
        "primary_anchor": {
            "name": primary.get('main_line'),
            "stage": primary.get('stage'),
            "score": primary.get('last_score'),
            "mid_cap": primary.get('mid_cap', []),
            "pioneer": primary.get('lianban_pioneer') or primary.get('trend_pioneer')
        },
        "challenger_anchor": {
            "name": challenger.get('main_line'),
            "stage": challenger.get('stage'),
            "score": challenger.get('last_score'),
            "mid_cap": challenger.get('mid_cap', []),
            "pioneer": challenger.get('lianban_pioneer') or challenger.get('trend_pioneer')
        } if challenger.get('main_line') else None,
        "market_environment": env,
        "key_signal": ""
    }
    if not any(h['date'] == today for h in history):
        history.append(entry)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

# ==================== 策略生成 ====================
def generate_strategy(data, anchor, main_lines, main_msg, mname, mstage):
    date_str = data['date']
    next_date = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')

    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    sh = data.get('sh_index', 0)
    m20 = data.get('ma20', 0)
    mlb = data.get('max_lianban', 0)

    cfg = json.load(open(CONFIG_FILE, 'r', encoding='utf-8')) if os.path.exists(CONFIG_FILE) else {}
    thresholds = cfg.get('environment_thresholds', {})
    S_amount = thresholds.get('S_amount', 22000)
    A_amount = thresholds.get('A_amount', 15000)
    S_lianban = thresholds.get('S_lianban', 5)

    if sh > m20 and total_amt > S_amount and mlb > S_lianban:
        env, max_cang = 'S', 4
    elif sh > m20 and total_amt >= A_amount:
        env, max_cang = 'A', 3
    else:
        env, max_cang = 'B', 2

    holdings = load_holdings()
    current_main = main_lines[0] if main_lines else {}
    current_roles = current_main.get('roles', {})

    # 读取评分历史
    scores_history = {}
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            scores_history = json.load(f)

    lines = []
    lines.append(f"# 豆包模式 · 自动盘前策略（{date_str} 复盘 -> {next_date}）")
    lines.append(f"\n> **环境等级**：{env}级 | 总仓位上限：仓{max_cang} | 生成时间：{datetime.now().strftime('%H:%M:%S')}")
    lines.append("\n## 1. 大盘状态")
    lines.append(f"- 上证：{sh:.2f}（{data.get('sh_pct', 0):+.2f}%），成交{data.get('sh_amount', 0):.0f}亿")
    lines.append(f"- 两市成交：{total_amt:.0f}亿")
    if 'up_count' in data:
        lines.append(f"- 涨跌家数：{data['up_count']}涨 / {data['down_count']}跌")
    lines.append(f"- 20日线：{m20:.2f}（{'站上' if sh > m20 else '跌破'}）")
    lines.append("\n## 2. 情绪周期")
    lines.append(f"- 涨停{data.get('limit_total', 0)} | 跌停{data.get('dieting_total', 0)} | 炸板{data.get('zhaban_total', 0)}")
    lines.append(f"- 最高连板：{mlb}连板")

    lines.append("\n## 3. 持仓处理与卖出建议")
    exit_lines = generate_exit_advice(holdings, mname, mstage, current_roles)
    lines.extend(exit_lines)

    lines.append("\n## 4. 主线评估与角色定位")
    lines.append(main_msg)
    for ml in main_lines[:3]:
        sym = "[OK]" if ml['score'] >= 4.5 else ("[WATCH]" if ml['score'] >= 4.0 else "[WARN]")
        style, style_note = determine_style(ml.get('roles', {}), data)
        lines.append(f"\n### {sym} {ml['name']}（{ml['score']}分，阶段：{ml['stage']}，风格：{style}）")
        lines.append(f"- {style_note}")

        # ---- 评分轨迹 ----
        name_key = ml['name']
        hist = scores_history.get(name_key, [])
        if hist:
            recent = hist[-5:]
            trail = " → ".join([f"{h['date'][-4:]}({h['score']})" for h in recent])
            lines.append(f"- 评分轨迹：{trail}")
        # -----------------

        roles = ml.get('roles', {})
        if ml['stage'] == 'C':
            lines.append("- 启动日，等待确认（需连续3日评分≥4.5）")
        elif 'G' in ml['stage']:
            lines.append("- 主升期，持有不加仓")
        elif 'D' in ml['stage']:
            lines.append("- 分歧期，观察活口")
        elif ml['stage'] == 'E':
            lines.append("- **退潮期，不参与**")
        else:
            lines.append("- 候选方向")
        if roles:
            mid = roles.get('mid_cap', [])
            lb = roles.get('lianban_pioneer')
            el = roles.get('elastic_pioneer')
            tr = roles.get('trend_pioneer')
            if mid:
                parts = [f"{m['name']}(成交{m.get('amount', 0):.0f}亿)" for m in mid]
                lines.append(f"- 核心中军：{', '.join(parts)}")
            if lb:
                lines.append(f"- 连板先锋(10cm)：{lb['name']}(封板{lb['first_time']}，换手{lb['turnover']}%，封单{lb['seal_amount']:.2f}亿)")
            if el:
                lines.append(f"- 弹性先锋(20cm)：{el['name']}({el['pct']}%，换手{el['turnover']}%)")
            if tr:
                lines.append(f"- 趋势先锋：{tr['name']}(趋势评分{tr.get('trend_score', 0):.1f}，量比{tr.get('lb', 1):.1f})")

    lines.append("\n## 5. 明日执行清单")
    lines.append(f"- 总仓位上限：{max_cang * 10}%")
    buy_signals = detect_buy_signals(main_lines, data, anchor)
    if not buy_signals:
        lines.append("\n**执行清单为空**（无符合买点的方向，继续观察）")
    else:
        for sig in buy_signals:
            lines.append(f"\n### {sig['name']}（{sig['type']}买点）")
            lines.append(f"- 仓位：**{sig['cangwei']}**")
            lines.append(f"- 标的：{', '.join(sig['stocks'])}")
            lines.append(f"- 触发条件：{sig['condition']}")
            if sig.get('timing'):
                lines.append(f"- 执行时间：{sig['timing']}")

    lines.append("\n---")
    lines.append(f"*本策略由豆包模式自动生成 v11.0*")

    try:
        save_replay_history(anchor, data, main_lines, env)
    except Exception as e:
        print(f"[警告] 保存历史记录失败: {e}")

    return '\n'.join(lines)