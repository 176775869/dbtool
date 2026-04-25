# coding=utf-8
"""
豆包模式 · 自动盘前策略生成器 v3.1 (全局锚点修正版)
- 全局唯一锚点（global_anchor.json）
- 候选方向评分独立存储（candidate_scores.json）
- 主线需连续3日评分≥4.5且中军走强
- 切换需挑战者连续3日评分超过主线且原主线中军走弱
- 退潮后等待新T日
- 修复：解析涨停个股，中军均线模糊匹配，策略输出至上一级目录
"""

import os
import re
import json
from datetime import datetime, timedelta

# ==================== 路径 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_ANCHOR_FILE = os.path.join(SCRIPT_DIR, 'global_anchor.json')
CANDIDATE_SCORES_FILE = os.path.join(SCRIPT_DIR, 'candidate_scores.json')
STRATEGY_OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..')  # 输出到上一级目录

# ==================== 参数配置 ====================
MIN_SCORE_MAIN_LINE = 4.5        # 主线最低评分（连续3天）
CONFIRM_DAYS = 3                  # 连续达标天数
SWITCH_DAYS = 3                   # 挑战者需连续超过天数
WEAK_DAYS = 2                     # 原主线中军连续走弱天数（破5日线）

# 政策强度关键词映射（可扩展）
POLICY_HINTS = {
    "锂矿": 4, "能源金属": 4, "算力": 5, "CPO": 5, "光模块": 5,
    "商业航天": 5, "航天": 5, "氦气": 4, "人工智能": 5,
    "芯片": 4, "半导体": 4, "光伏": 3, "风电": 3, "储能": 3,
    "机器人": 4, "无人驾驶": 4, "氟化工": 3, "PVDF": 3, "磷化工": 3,
}

EXCLUDE_CONCEPTS = [
    "昨日首板", "昨日涨停", "昨日连板", "昨日触板",
    "微盘股", "微盘精选", "ST股", "低价股", "破净股",
    "2026—季报扭亏", "举牌", "青蒿素",
]

# 中军映射（用于顶部成交额匹配）
MID_CAP_MAP = {
    "锂矿": ["宁德时代", "天齐锂业", "赣锋锂业", "永兴材料"],
    "能源金属": ["宁德时代", "天齐锂业", "赣锋锂业"],
    "算力": ["工业富联", "中际旭创", "新易盛", "海光信息"],
    "CPO": ["中际旭创", "新易盛", "天孚通信"],
    "光模块": ["中际旭创", "新易盛"],
    "商业航天": ["中国卫星", "中国卫通"],
    "氟化工": ["巨化股份", "多氟多"],
    "PVDF": ["多氟多"],
    "磷化工": ["云天化", "兴发集团"],
    "氦气": ["凯美特气", "华特气体"],
}

# ==================== 文件读写 ====================
def find_latest_replay():
    files = [f for f in os.listdir(SCRIPT_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        raise FileNotFoundError("未找到复盘数据包")
    files.sort(reverse=True)
    return os.path.join(SCRIPT_DIR, files[0])

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 数据解析 ====================
def parse_replay(filepath):
    """解析 replay_full_*.txt 数据包"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    data = {}

    # 日期
    date_match = re.search(r'日期: (\d{8})', content)
    if date_match:
        data['date'] = date_match.group(1)

    # 指数信息
    sh_match = re.search(r'上证指数: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if sh_match:
        data['sh_index'] = float(sh_match.group(1))
        data['sh_pct'] = float(sh_match.group(2))
        data['sh_amount'] = float(sh_match.group(3))
    sz_match = re.search(r'深证成指: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if sz_match:
        data['sz_amount'] = float(sz_match.group(3))
    cy_match = re.search(r'创业板指: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if cy_match:
        data['cy_index'] = float(cy_match.group(1))
    ma20_match = re.search(r'上证20日均线: ([\d.]+)', content)
    if ma20_match:
        data['ma20'] = float(ma20_match.group(1))
    uv_match = re.search(r'两市上涨家数: (\d+)，下跌家数: (\d+)', content)
    if uv_match:
        data['up_count'] = int(uv_match.group(1))
        data['down_count'] = int(uv_match.group(2))

    # 涨停概览
    limit_total_match = re.search(r'涨停总数: (\d+)', content)
    if limit_total_match:
        data['limit_total'] = int(limit_total_match.group(1))
    max_lb_match = re.search(r'最高连板: (\d+)连板', content)
    if max_lb_match:
        data['max_lianban'] = int(max_lb_match.group(1))
    zhaban_match = re.search(r'炸板总数: (\d+)', content)
    if zhaban_match:
        data['zhaban_total'] = int(zhaban_match.group(1))
    dieting_match = re.search(r'跌停总数: (\d+)', content)
    if dieting_match:
        data['dieting_total'] = int(dieting_match.group(1))

    # 涨停个股列表（用于先锋封单）
    limit_stocks = []
    # 从涨停数据表格中解析（表格位于第一个“涨停总数”之后的区块）
    limit_table = re.search(
        r'涨停总数: \d+\n最高连板: \d+连板.*?\n-+\n(.*?)(?:\n\n日期:|\n\n炸板)',
        content, re.DOTALL
    )
    if limit_table:
        for line in limit_table.group(1).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 11:
                try:
                    limit_stocks.append({
                        'name': parts[1],
                        'code': parts[2],
                        'pct': float(parts[3].replace('%', '')),
                        'lianban': int(parts[4].replace('板', '')),
                        'first_time': parts[6],
                        'turnover': float(parts[8].replace('%', '')),
                        'amount': float(parts[9].replace('亿', '')),
                        'seal_amount': float(parts[10].replace('亿', '')) if parts[10] != '--' else 0
                    })
                except:
                    pass
    data['limit_stocks'] = limit_stocks

    # 概念板块涨幅前20
    con_sec = re.search(r'=== 概念板块涨幅前20 ===\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    concepts = []
    if con_sec:
        for line in con_sec.group(1).strip().split('\n'):
            if ': ' in line:
                name, rest = line.split(': ', 1)
                pct_m = re.search(r'([+\-][\d.]+)%', rest)
                amt_m = re.search(r'成交([\d.]+)亿', rest)
                lead_m = re.search(r'领涨:(.+)', rest)
                if pct_m:
                    concepts.append({
                        'name': name.strip(),
                        'pct': float(pct_m.group(1)),
                        'amount': float(amt_m.group(1)) if amt_m else 0,
                        'leader': lead_m.group(1).strip() if lead_m else ''
                    })
    data['concepts'] = concepts

    # 板块涨停家数统计
    st_sec = re.search(r'板块涨停家数统计\n-+\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    limit_by_sector = {}
    if st_sec:
        for line in st_sec.group(1).strip().split('\n'):
            m = re.match(r'^(.+?):\s*(\d+)只涨停', line.strip())
            if m:
                limit_by_sector[m.group(1).strip()] = int(m.group(2))
    data['limit_by_sector'] = limit_by_sector

    # 板块均线
    ma_sec = re.search(r'板块均线状态.*?\n\n((?:.+\n)+?)(?:\n日期:|$)', content, re.DOTALL)
    sector_ma = {}
    if ma_sec:
        for line in ma_sec.group(1).strip().split('\n'):
            m = re.match(r'^(.+?)\(BK\d+\):.*MA5=(\d+\.?\d*)\((\w+)\).*MA20=(\d+\.?\d*)\((\w+)\)', line)
            if m:
                sector_ma[m.group(1).strip()] = {
                    'ma5': float(m.group(2)),
                    'ma5_status': m.group(3),
                    'ma20': float(m.group(4)),
                    'ma20_status': m.group(5)
                }
    data['sector_ma'] = sector_ma

    # 核心中军行情
    mid_sec = re.search(r'核心中军行情.*?\n\n(.*?)(?:\n\n日期:|\n\n全市场)', content, re.DOTALL)
    mid_caps = []
    if mid_sec:
        for line in mid_sec.group(1).strip().split('\n'):
            m = re.search(r'^(.+?)\((\d+)\): ([\d.]+) ([+\-][\d.]+)% 成交([\d.]+)亿', line)
            if m:
                mid_caps.append({
                    'name': m.group(1), 'code': m.group(2),
                    'price': float(m.group(3)), 'pct': float(m.group(4)),
                    'amount': float(m.group(5))
                })
    data['mid_caps'] = mid_caps

    # 全市场成交额Top20
    top_sec = re.search(r'全市场成交额Top20\n\n(.*?)(?:\n\n===)', content, re.DOTALL)
    top20 = []
    if top_sec:
        for line in top_sec.group(1).strip().split('\n'):
            m = re.search(r'\d+\. (.+?)\((\d+)\): ([+\-][\d.]+)% 成交([\d.]+)亿 总市值([\d.]+)亿', line)
            if m:
                top20.append({
                    'name': m.group(1), 'code': m.group(2),
                    'pct': float(m.group(3)), 'amount': float(m.group(4)),
                    'market_cap': float(m.group(5))
                })
    data['top20'] = top20

    return data

# ==================== 评分与中军 ====================
def get_policy_strength(concept_name):
    for key, score in POLICY_HINTS.items():
        if key in concept_name:
            return score
    return 3

def calc_sector_score(concept, data):
    """计算单个概念板块的评分（0-5）"""
    name = concept['name']
    policy = get_policy_strength(name)

    # 资金流入得分（板块涨幅超过3%视为资金认可）
    pct = concept['pct']
    if pct > 5:
        money_score = 5
    elif pct > 2:
        money_score = 3
    else:
        money_score = 1

    # 涨停数量得分（从板块涨停家数统计中获取）
    limit_cnt = data.get('limit_by_sector', {}).get(name, 0)
    # 若板块名称不在统计中（如概念板块与行业板块统计不匹配），尝试模糊匹配
    if limit_cnt == 0:
        for sec_name, cnt in data.get('limit_by_sector', {}).items():
            if name in sec_name or sec_name in name:
                limit_cnt = cnt
                break
    if limit_cnt >= 10:
        limit_score = 5
    elif limit_cnt >= 5:
        limit_score = 3
    else:
        limit_score = 1

    # 先锋封单得分（取领涨股的封单额）
    seal = 0
    leader = concept.get('leader', '')
    # 优先从涨停个股中精确查找
    for st in data.get('limit_stocks', []):
        if st.get('name') == leader:
            seal = st.get('seal_amount', 0)
            break
    # 未找到则尝试从所有涨停股中找匹配
    if seal == 0:
        for st in data.get('limit_stocks', []):
            if leader in st.get('name', '') or st.get('name', '') in leader:
                seal = st.get('seal_amount', 0)
                break
    if seal > 5:
        seal_score = 5
    elif seal > 1:
        seal_score = 3
    else:
        seal_score = 1

    # 中军表现得分
    mid_candidates = []
    for key, names in MID_CAP_MAP.items():
        if key in name:
            for n in names:
                for st in data.get('top20', []) + data.get('mid_caps', []):
                    if st['name'] == n:
                        mid_candidates.append(st)
    if mid_candidates:
        avg_pct = sum(s['pct'] for s in mid_candidates) / len(mid_candidates)
        if avg_pct >= 9.8:
            mid_score = 5
        elif avg_pct > 5:
            mid_score = 3
        else:
            mid_score = 2
    else:
        mid_score = 1

    total = (policy * 0.2 + money_score * 0.3 + limit_score * 0.2 +
             seal_score * 0.15 + mid_score * 0.15)
    return round(total, 2)

def get_sector_mid_trend(concept_name, data):
    """获取板块中军是否破5日线（支持模糊匹配）"""
    ma_info = data.get('sector_ma', {})
    # 精确匹配
    if concept_name in ma_info:
        info = ma_info[concept_name]
        return (info.get('ma5_status') == '已跌破'), (info.get('ma20_status') == '已跌破')
    # 模糊匹配
    for key, val in ma_info.items():
        if concept_name in key or key in concept_name:
            return (val.get('ma5_status') == '已跌破'), (val.get('ma20_status') == '已跌破')
    return False, False

# ==================== 主线与锚点管理 ====================
def update_candidate_scores(candidates, data):
    """更新候选方向评分历史"""
    scores = load_json(CANDIDATE_SCORES_FILE)
    today = data['date']
    for cand in candidates:
        name = cand['name']
        score = calc_sector_score(cand, data)
        if name not in scores:
            scores[name] = []
        scores[name].append({'date': today, 'score': score})
        # 保留最近10天
        scores[name] = scores[name][-10:]
    save_json(CANDIDATE_SCORES_FILE, scores)
    return scores

def get_main_line_from_anchor(global_anchor):
    """返回 (主线名称, 阶段, 最后评分, T日)"""
    if not global_anchor or 'main_line' not in global_anchor:
        return None, None, None, None
    main = global_anchor['main_line']
    return main.get('name'), main.get('stage'), main.get('last_score'), global_anchor.get('t_day')

def update_global_anchor(global_anchor, new_main_line, new_stage, new_score, new_t_day=None):
    """更新全局锚点"""
    global_anchor['main_line'] = {
        'name': new_main_line,
        'stage': new_stage,
        'last_score': new_score
    }
    if new_t_day:
        global_anchor['t_day'] = new_t_day
    # 记录历史变更（可选）
    if 'history' not in global_anchor:
        global_anchor['history'] = []
    global_anchor['history'].append({
        'date': new_t_day or global_anchor.get('t_day'),
        'main_line': new_main_line,
        'stage': new_stage,
        'score': new_score
    })
    save_json(GLOBAL_ANCHOR_FILE, global_anchor)

def check_main_line_confirmation(candidate_name, scores_history, data):
    """检查候选方向是否满足成为主线的条件：连续3日评分>=4.5且中军未破5日线"""
    if len(scores_history) < CONFIRM_DAYS:
        return False
    recent = [s['score'] for s in scores_history[-CONFIRM_DAYS:]]
    if all(s >= MIN_SCORE_MAIN_LINE for s in recent):
        ma5_broken, _ = get_sector_mid_trend(candidate_name, data)
        if not ma5_broken:
            return True
    return False

def check_main_line_switch(challenger_name, challenger_scores, main_name, main_score, data):
    """检查挑战者是否满足切换条件：连续3日评分>当前主线且中军走强，同时原主线中军走弱"""
    if len(challenger_scores) < SWITCH_DAYS:
        return False
    recent = [s['score'] for s in challenger_scores[-SWITCH_DAYS:]]
    if all(s > main_score for s in recent):
        chal_ma5_broken, _ = get_sector_mid_trend(challenger_name, data)
        main_ma5_broken, _ = get_sector_mid_trend(main_name, data)
        # 挑战者中军未破位，原主线中军破位
        if not chal_ma5_broken and main_ma5_broken:
            return True
    return False

def determine_main_lines(global_anchor, candidate_scores, data):
    """核心逻辑：确定当前主线与阶段"""
    today = data['date']
    main_name, main_stage, main_score, t_day = get_main_line_from_anchor(global_anchor)

    # 1. 收集今日所有候选板块及其评分
    candidates = [(c['name'], calc_sector_score(c, data)) for c in data.get('concepts', [])]
    candidates.sort(key=lambda x: x[1], reverse=True)
    # 排除噪声概念
    candidates = [c for c in candidates if not any(ex in c[0] for ex in EXCLUDE_CONCEPTS)]

    # 更新候选评分历史
    candidate_scores = update_candidate_scores(data.get('concepts', []), data)

    # 无主线或主线已退潮
    if not main_name or main_stage == 'E':
        for cand_name, _ in candidates:
            hist = candidate_scores.get(cand_name, [])
            if check_main_line_confirmation(cand_name, hist, data):
                new_score = calc_sector_score({'name': cand_name}, data)
                update_global_anchor(global_anchor, cand_name, 'C', new_score, today)
                main_name = cand_name
                main_stage = 'C'
                main_score = new_score
                t_day = today
                break
        else:
            return [], "无确认主线，候选方向等待验证"

    # 2. 有主线，计算今日主线评分并阶段递推
    main_today_score = next((s for n,s in candidates if n==main_name), main_score)
    ma5_broken, ma20_broken = get_sector_mid_trend(main_name, data)

    # 阶段递推
    if main_stage == 'C':
        if main_today_score >= 4.5 and not ma5_broken:
            new_stage = '1G-1'
        else:
            new_stage = 'C'
    elif 'G' in main_stage:
        if ma5_broken:
            num = int(main_stage.split('-')[0][0])
            new_stage = f'{num}D-1'
        else:
            parts = main_stage.split('-')
            new_day = int(parts[1]) + 1 if len(parts)>1 else 1
            new_stage = f"{parts[0]}-{new_day}"
    elif 'D' in main_stage:
        if not ma5_broken and main_today_score >= 4.0:
            num = int(main_stage.split('-')[0][0]) + 1
            new_stage = f'{num}G-1'
        else:
            parts = main_stage.split('-')
            new_day = int(parts[1]) + 1
            new_stage = f"{parts[0]}-{new_day}"
    elif main_stage == 'E':
        new_stage = 'E'
    else:
        new_stage = main_stage

    if main_today_score < 3.0 and ma20_broken:
        new_stage = 'E'

    update_global_anchor(global_anchor, main_name, new_stage, main_today_score)

    # 3. 检查是否有挑战者切换主线
    for cand_name, _ in candidates:
        if cand_name == main_name:
            continue
        hist = candidate_scores.get(cand_name, [])
        if check_main_line_switch(cand_name, hist, main_name, main_score, data):
            new_score = calc_sector_score({'name': cand_name}, data)
            update_global_anchor(global_anchor, cand_name, 'C', new_score, today)
            main_name = cand_name
            new_stage = 'C'
            break

    output = []
    main_score_today = calc_sector_score({'name': main_name}, data)
    output.append({
        'name': main_name,
        'score': main_score_today,
        'stage': new_stage,
        'detail': {}
    })
    for cand_name, sc in candidates[:5]:
        if cand_name != main_name and sc >= 3.0:
            output.append({
                'name': cand_name,
                'score': sc,
                'stage': '候选',
                'detail': {}
            })
    return output, f"主线：{main_name}（{new_stage}）"

# ==================== 策略生成 ====================
def generate_strategy(data, global_anchor):
    date_str = data['date']
    next_date = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    # 环境等级
    if data.get('sh_index', 0) > data.get('ma20', 0) and total_amt > 22000 and data.get('max_lianban', 0) > 5:
        env = 'S'
        max_cang = 4
    elif data.get('sh_index', 0) > data.get('ma20', 0) and total_amt >= 15000:
        env = 'A'
        max_cang = 3
    else:
        env = 'B'
        max_cang = 2

    main_lines, main_msg = determine_main_lines(global_anchor, {}, data)

    lines = []
    lines.append(f"# 豆包模式 · 自动盘前策略（{date_str} 复盘 → {next_date}）")
    lines.append(f"\n> **环境等级**：{env}级 | 总仓位上限：仓{max_cang} | 生成时间：{datetime.now().strftime('%H:%M:%S')}")
    lines.append("")
    lines.append("## 1️⃣ 大盘状态")
    lines.append(f"- 上证：{data['sh_index']:.2f}（{data.get('sh_pct',0):+.2f}%），成交{data['sh_amount']:.0f}亿")
    lines.append(f"- 两市成交：{total_amt:.0f}亿")
    if 'up_count' in data:
        lines.append(f"- 涨跌家数：{data['up_count']}涨 / {data['down_count']}跌")
    lines.append(f"- 20日线：{data['ma20']:.2f}（{'站上' if data['sh_index'] > data['ma20'] else '跌破'}）")
    lines.append("")
    lines.append("## 2️⃣ 情绪周期")
    lines.append(f"- 涨停{data.get('limit_total',0)} | 跌停{data.get('dieting_total',0)} | 炸板{data.get('zhaban_total',0)}")
    lines.append(f"- 最高连板：{data.get('max_lianban',0)}连板")
    lines.append("")
    lines.append("## 3️⃣ 主线评估")
    lines.append(f"{main_msg}")
    for ml in main_lines[:3]:
        symbol = "✅" if ml['score'] >= 4.5 else ("⏳" if ml['score'] >= 4.0 else "⚠️")
        lines.append(f"\n### {symbol} {ml['name']}（{ml['score']}分，阶段：{ml['stage']}）")
        if ml['stage'] == 'C':
            lines.append("- 启动日，等待确认（需连续3日评分≥4.5且中军走强）")
        elif 'G' in ml['stage']:
            lines.append("- 主升期，持有不加仓（若已持仓）")
        elif 'D' in ml['stage']:
            lines.append("- 分歧期，观察为主，等待弱转强信号")
        else:
            lines.append("- 候选方向，观察持续性")

    lines.append("\n## 4️⃣ 明日执行清单")
    lines.append(f"- 总仓位上限：{max_cang*10}% | 当前持仓：建议空仓")
    for ml in main_lines:
        if ml['stage'] == 'C':
            lines.append(f"\n### {ml['name']}（C日→等待确认）")
            lines.append("- 关注确认信号：板块涨停≥10家、中军大涨＞7%、成交放大 → 执行买点C类型B")
        elif ml['stage'] in ('1G-1','2G-1','3G-1'):
            lines.append(f"\n### {ml['name']}（弱转强确认日）")
            lines.append("- 可执行D2/D3买点，仓位仓2-仓3")
    if not any(ml['stage'] in ('C','1G-1','2G-1','3G-1') for ml in main_lines):
        lines.append("\n**执行清单为空**（无符合买点的方向）")

    lines.append("\n---")
    lines.append(f"*本策略由豆包模式自动生成，锚点数据已保存至 {GLOBAL_ANCHOR_FILE}*")
    return '\n'.join(lines)

def main():
    replay_file = find_latest_replay()
    print(f"📂 读取: {replay_file}")
    data = parse_replay(replay_file)
    print("✅ 解析完成")

    global_anchor = load_json(GLOBAL_ANCHOR_FILE)
    if not global_anchor:
        global_anchor = {
            "t_day": None,
            "main_line": {"name": None, "stage": "E", "last_score": 0},
            "history": []
        }
        save_json(GLOBAL_ANCHOR_FILE, global_anchor)

    strategy = generate_strategy(data, global_anchor)

    next_date = (datetime.strptime(data['date'], '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    # 输出到上一级目录
    os.makedirs(STRATEGY_OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(STRATEGY_OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(strategy)
    print(f"📝 策略已保存: {out_file}")
    print("\n--- 预览（前800字符） ---")
    print(strategy[:800])

if __name__ == '__main__':
    main()