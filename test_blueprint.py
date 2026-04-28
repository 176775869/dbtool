# coding=utf-8
"""
独立测试脚本：验证双锚点 + 方向过滤角色识别的完整逻辑。
读取最新的 replay_full 数据包，输出完整的策略结果。
"""
import os, re, json
from datetime import datetime, timedelta

# ==================== 路径 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'py', 'data')
CONFIG_DIR = os.path.join(SCRIPT_DIR, 'py', 'config')

# ==================== 加载配置 ====================
def load_config():
    config_file = os.path.join(CONFIG_DIR, 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

cfg = load_config()
CLUSTER_KW = cfg.get('cluster_keywords', {})
POLICY_HINTS = cfg.get('policy_hints', {})
OLD_MAIN = cfg.get('old_main_names', [])

# ==================== 查找最新数据包 ====================
def find_latest_replay():
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        return None
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])

# ==================== 数据解析（精简版，只取关键字段） ====================
def parse_replay(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    data = {}

    # 日期
    m = re.search(r'日期: (\d{8})', content)
    if m: data['date'] = m.group(1)

    # 上证
    m = re.search(r'上证指数: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if m: data['sh_index'], data['sh_pct'], data['sh_amount'] = float(m.group(1)), float(m.group(2)), float(m.group(3))

    # 深证成交额
    m = re.search(r'深证成指: [\d.]+\D+([+\-][\d.]+)%\D+([\d.]+)亿', content)
    if not m:
        m = re.search(r'深证成指: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if m:
        try:
            if len(m.groups()) == 2: data['sz_amount'] = float(m.group(2))
            else: data['sz_amount'] = float(m.group(3))
        except: data['sz_amount'] = 0

    # 20日线
    m = re.search(r'上证20日均线: ([\d.]+)', content)
    if m: data['ma20'] = float(m.group(1))

    # 涨跌家数
    m = re.search(r'两市上涨家数: (\d+)，下跌家数: (\d+)', content)
    if m: data['up_count'], data['down_count'] = int(m.group(1)), int(m.group(2))

    # 涨停/跌停/炸板总数
    for k, p in [('limit_total', r'涨停总数: (\d+)'), ('max_lianban', r'最高连板: (\d+)连板'),
                 ('zhaban_total', r'炸板总数: (\d+)'), ('dieting_total', r'跌停总数: (\d+)')]:
        m = re.search(p, content)
        if m: data[k] = int(m.group(1))

    # 涨停个股（用于角色识别）
    limit_table = re.search(r'涨停总数: \d+\n最高连板: \d+连板.*?\n-+\n(.*?)(?:\n\n日期:|\n\n炸板)', content, re.DOTALL)
    limit_stocks = []
    if limit_table:
        for line in limit_table.group(1).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 11:
                try:
                    rt = parts[6].strip()
                    limit_stocks.append({
                        'name': parts[1], 'code': parts[2],
                        'pct': float(parts[3].replace('%','')),
                        'lianban': int(parts[4].replace('板','')),
                        'first_time': rt if rt != '--' else '15:00',
                        'turnover': float(parts[8].replace('%','')),
                        'amount': float(parts[9].replace('亿','')),
                        'seal_amount': float(parts[10].replace('亿','')) if parts[10] != '--' else 0
                    })
                except: pass
    data['limit_stocks'] = limit_stocks

    # Top20（用于中军识别）
    tsec = re.search(r'全市场成交额Top20\n\n(.*?)(?:\n\n===)', content, re.DOTALL)
    top20 = []
    if tsec:
        for line in tsec.group(1).strip().split('\n'):
            m = re.search(r'\d+\. (.+?)\((\d+)\): ([+\-][\d.]+)% 成交([\d.]+)亿 总市值([\d.]+)亿', line)
            if m:
                top20.append({
                    'name': m.group(1), 'code': m.group(2),
                    'pct': float(m.group(3)), 'amount': float(m.group(4)),
                    'market_cap': float(m.group(5))
                })
    data['top20'] = top20

    # 核心中军行情（补充中军池）
    msec = re.search(r'核心中军行情.*?\n\n(.*?)(?:\n\n日期:|\n\n全市场)', content, re.DOTALL)
    mid_caps = []
    if msec:
        for line in msec.group(1).strip().split('\n'):
            m = re.search(r'^(.+?)\((\d+)\): ([\d.]+) ([+\-][\d.]+)% 成交([\d.]+)亿', line)
            if m:
                mid_caps.append({
                    'name': m.group(1), 'code': m.group(2),
                    'price': float(m.group(3)), 'pct': float(m.group(4)),
                    'amount': float(m.group(5)), 'market_cap': 0  # 中军行情没有市值字段，默认0
                })
    data['mid_caps'] = mid_caps

    # 概念板块（用于评分）
    csec = re.search(r'=== 概念板块涨幅前20 ===\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    concepts = []
    if csec:
        for line in csec.group(1).strip().split('\n'):
            if ': ' in line:
                name, rest = line.split(': ', 1)
                pm = re.search(r'([+\-][\d.]+)%', rest)
                if pm:
                    concepts.append({'name': name.strip(), 'pct': float(pm.group(1))})
    data['concepts'] = concepts

    # 强势股池（用于趋势先锋）
    qsec = re.search(r'强势股总数: (\d+)\n\n-+\n(.*?)(?:\n\n日期:|\n\n===|$)', content, re.DOTALL)
    qs = []
    if qsec:
        for line in qsec.group(2).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 9:
                try:
                    qs.append({
                        'name': parts[1], 'code': parts[2],
                        'pct': float(parts[3].replace('%','')),
                        'turnover': float(parts[4].replace('%','')),
                        'amount': float(parts[5].replace('亿','')),
                        'lb': float(parts[6]),
                        'nh': int(parts[7]),
                        'trend_score': float(parts[8])
                    })
                except: pass
    data['qs_stocks'] = qs

    return data

# ==================== 角色识别（方向过滤 + 兜底） ====================
def identify_roles(direction_name, data):
    limit_stocks = data.get('limit_stocks', [])
    all_mid = data.get('top20', []) + data.get('mid_caps', [])
    qs = data.get('qs_stocks', [])
    kw_list = CLUSTER_KW.get(direction_name, [])
    if not kw_list:
        kw_list = [direction_name[:4]]

    def is_related(name):
        return any(kw in name for kw in kw_list)

    # ---- 中军 ----
    seen = set()
    mids = []
    for obj in all_mid:
        code = obj.get('code', '')
        if code in seen: continue
        # 市值：top20有market_cap字段，mid_caps可能没有，默认设为0（不符合>200条件）
        market_cap = obj.get('market_cap', 0)
        if market_cap == 0 and 'name' in obj and obj['name'] in [o['name'] for o in data.get('top20', [])]:
            # 从top20中再次确认市值
            for t in data.get('top20', []):
                if t['code'] == code:
                    market_cap = t.get('market_cap', 0)
                    break
        if market_cap >= 200 and obj['pct'] >= 3 and is_related(obj['name']):
            mids.append(obj)
            seen.add(code)

    # 兜底：放宽至市值>100亿 + 涨幅>=1%
    if not mids:
        for obj in all_mid:
            code = obj.get('code', '')
            if code in seen: continue
            market_cap = obj.get('market_cap', 0)
            # 对于mid_caps，市值可能为0，尝试用name匹配top20获取市值
            if market_cap == 0:
                for t in data.get('top20', []):
                    if t['code'] == code:
                        market_cap = t.get('market_cap', 0)
                        break
            if market_cap >= 100 and obj['pct'] >= 1 and is_related(obj['name']):
                mids.append(obj)
                seen.add(code)

    mids.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
    mids = mids[:3]

    # ---- 连板先锋 / 弹性先锋 ----
    rel_limit = [s for s in limit_stocks if is_related(s['name'])]
    def score_lb(st):
        t = st['turnover']
        ts = 10 if 3 <= t <= 7 else (7 if 7 < t <= 15 else (3 if t < 3 else 2))
        try:
            h, m = map(int, st['first_time'].split(':'))
            mins = h * 60 + m
        except: mins = 999
        ti = (10 if mins <= 570 else 9 if mins <= 600 else 7 if mins <= 630 else 5 if mins <= 690 else 2)
        sr = st['seal_amount'] / st['amount'] if st['amount'] > 0 else 0
        se = 9 if sr > 3 else (7 if sr > 2 else (5 if sr > 1 else 3))
        is_10cm = not st['code'].startswith(('300', '688', '301'))
        return ts * 0.3 + ti * 0.3 + se * 0.2 + (5 if is_10cm else -5) * 0.2, st

    lianban, elastic = None, None
    if rel_limit:
        scored = [score_lb(s) for s in rel_limit]
        scored.sort(key=lambda x: x[0], reverse=True)
        top1 = scored[0][1]
        if top1['code'].startswith(('300', '688', '301')):
            elastic = top1
            for sc, st in scored:
                if not st['code'].startswith(('300', '688', '301')):
                    lianban = st
                    break
        else:
            lianban = top1
            for sc, st in scored:
                if st['code'].startswith(('300', '688', '301')):
                    elastic = st
                    break

    # ---- 趋势先锋 ----
    rel_qs = [s for s in qs if is_related(s['name'])]
    trend = None
    cands = [q for q in rel_qs if q.get('lb', 0) >= 1.5]
    valid = [q for q in cands if not any(ls['code'] == q['code'] and ls['lianban'] > 2 for ls in limit_stocks)]
    if valid:
        valid.sort(key=lambda x: x.get('trend_score', 0), reverse=True)
        trend = valid[0]

    return {
        'mid_cap': mids,
        'lianban_pioneer': lianban,
        'elastic_pioneer': elastic,
        'trend_pioneer': trend
    }

# ==================== 主流程 ====================
def main():
    replay_file = find_latest_replay()
    if not replay_file:
        print("未找到 replay_full 数据包")
        return

    print(f"[读取] {replay_file}")
    data = parse_replay(replay_file)

    # -------------------- 调试：打印 top20 前三条的原始字段 --------------------
    print("\n===== DEBUG: Top20 前三条 =====")
    top20 = data.get('top20', [])
    with open(replay_file, 'r', encoding='utf-8') as f:
        content = f.read()
    # 提取 Top20 区块的原始文本
    tsec = re.search(r'全市场成交额Top20\n\n(.*?)(?:\n\n===)', content, re.DOTALL)
    if tsec:
        lines = tsec.group(1).strip().split('\n')[:3]
        for i, line in enumerate(lines):
            print(f"  第{i+1}行原始文本: {line}")
            # 同时打印解析结果
            if i < len(top20):
                print(f"  解析结果: {top20[i]}")
    # ---------------------------------------------------------------

    # 读取双锚点
    anchor_file = os.path.join(CONFIG_DIR, 'global_anchor.json')
    anchor = {}
    if os.path.exists(anchor_file):
        with open(anchor_file, 'r', encoding='utf-8') as f:
            anchor = json.load(f)

    challenger = anchor.get('challenger_anchor') or {}
    primary = anchor.get('primary_anchor') or {}

    if challenger.get('main_line'):
        direction = challenger['main_line']
        stage = challenger.get('stage', 'C')
        msg = f"挑战者：{direction}（{stage}）"
    elif primary.get('main_line'):
        direction = primary['main_line']
        stage = primary.get('stage', '?')
        msg = f"主线：{direction}（{stage}）"
    else:
        print("无主线，无法识别角色")
        return

    print(f"\n当前方向: {direction}")
    print(f"阶段: {stage}")

    roles = identify_roles(direction, data)

    print(f"\n===== 角色识别结果 =====")
    print(f"中军: {[m['name'] for m in roles['mid_cap']]}")
    print(f"连板先锋: {roles['lianban_pioneer']['name'] if roles['lianban_pioneer'] else '无'}")
    print(f"弹性先锋: {roles['elastic_pioneer']['name'] if roles['elastic_pioneer'] else '无'}")
    print(f"趋势先锋: {roles['trend_pioneer']['name'] if roles['trend_pioneer'] else '无'}")

if __name__ == '__main__':
    main()