# coding=utf-8
"""
豆包模式 · 自动盘前策略生成器 v5.6 (终极修复版)
- 确保两市成交额 = 上证 + 深证
- 优化深证成交额的正则匹配，并增加容错
"""
import os, re, json
from datetime import datetime, timedelta

# -------------------- 路径 --------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_ANCHOR_FILE = os.path.join(SCRIPT_DIR, 'global_anchor.json')
CANDIDATE_SCORES_FILE = os.path.join(SCRIPT_DIR, 'candidate_scores.json')
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..')
LOCK_FILE = os.path.join(SCRIPT_DIR, 'last_strategy_date.txt')

MIN_SCORE_MAIN_LINE = 4.5
CONFIRM_DAYS = 3
SWITCH_DAYS = 3
DECLINE_DAYS = 2

# -------------------- 配置加载 --------------------
def load_config():
    default = {"policy_hints": {}, "mid_cap_map": {}, "exclude_concepts": [], "current_holdings": {}}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            for k, v in default.items():
                if k not in cfg: cfg[k] = v
            return cfg
    return default

CFG = load_config()
POLICY_HINTS = CFG['policy_hints']
MID_CAP_MAP = CFG['mid_cap_map']
EXCLUDE_CONCEPTS = CFG['exclude_concepts']
CURRENT_HOLDINGS = CFG['current_holdings']

# -------------------- 工具函数 --------------------
def find_latest_replay():
    files = [f for f in os.listdir(SCRIPT_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files: raise FileNotFoundError("未找到复盘数据包")
    files.sort(reverse=True)
    return os.path.join(SCRIPT_DIR, files[0])

def load_json(fp):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

# -------------------- 数据解析 --------------------
def parse_replay(fp):
    with open(fp, 'r', encoding='utf-8') as f: content = f.read()
    data = {}
    m = re.search(r'日期: (\d{8})', content)
    if m: data['date'] = m.group(1)

    # 上证指数
    m = re.search(r'上证指数: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if m: data['sh_index'], data['sh_pct'], data['sh_amount'] = float(m.group(1)), float(m.group(2)), float(m.group(3))
    
    # 深证成指 - 修复后的匹配
    m = re.search(r'深证成指: [\d.]+\D+([+\-][\d.]+)%\D+([\d.]+)亿', content) # 通用匹配
    if not m:
        # 如果通用匹配失败，尝试精确匹配（兼容可能的格式变化）
        m = re.search(r'深证成指: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    
    if m:
        # 如果匹配到，成交额在最后一个捕获组
        try:
            # 通用匹配的捕获组顺序：涨幅, 成交额
            # 精确匹配的捕获组顺序：指数, 涨幅, 成交额
            # 通过捕获组数量判断
            if len(m.groups()) == 2:
                data['sz_amount'] = float(m.group(2))
            else:
                data['sz_amount'] = float(m.group(3))
        except:
            data['sz_amount'] = 0
    else:
        data['sz_amount'] = 0
        # 调试提示
        print("[警告] 未找到深证成指成交额，请检查 replay_full 文件格式。")
        # 找到深证成指行并打印出来
        for line in content.split('\n'):
            if '深证成指' in line:
                print(f"  找到深证行: {line.strip()}")
                break

    m = re.search(r'上证20日均线: ([\d.]+)', content)
    if m: data['ma20'] = float(m.group(1))
    m = re.search(r'两市上涨家数: (\d+)，下跌家数: (\d+)', content)
    if m: data['up_count'], data['down_count'] = int(m.group(1)), int(m.group(2))

    for k, p in [('limit_total', r'涨停总数: (\d+)'), ('max_lianban', r'最高连板: (\d+)连板'),
                 ('zhaban_total', r'炸板总数: (\d+)'), ('dieting_total', r'跌停总数: (\d+)')]:
        m = re.search(p, content)
        if m: data[k] = int(m.group(1))

    # 涨停个股
    limit_stocks = []
    limit_table = re.search(r'涨停总数: \d+\n最高连板: \d+连板.*?\n-+\n(.*?)(?:\n\n日期:|\n\n炸板)', content, re.DOTALL)
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

    # 概念板块
    csec = re.search(r'=== 概念板块涨幅前20 ===\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    concepts = []
    if csec:
        for line in csec.group(1).strip().split('\n'):
            if ': ' in line:
                name, rest = line.split(': ', 1)
                pm = re.search(r'([+\-][\d.]+)%', rest)
                am = re.search(r'成交([\d.]+)亿', rest)
                lm = re.search(r'领涨:(.+)', rest)
                if pm:
                    concepts.append({'name': name.strip(), 'pct': float(pm.group(1)),
                                     'amount': float(am.group(1)) if am else 0,
                                     'leader': lm.group(1).strip() if lm else ''})
    data['concepts'] = concepts

    # 板块涨停统计
    ssec = re.search(r'板块涨停家数统计\n-+\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    lbs = {}
    if ssec:
        for line in ssec.group(1).strip().split('\n'):
            m = re.match(r'^(.+?):\s*(\d+)只涨停', line.strip())
            if m: lbs[m.group(1).strip()] = int(m.group(2))
    data['limit_by_sector'] = lbs

    # 板块均线
    msec = re.search(r'板块均线状态.*?\n\n((?:.+\n)+?)(?:\n日期:|$)', content, re.DOTALL)
    sma = {}
    if msec:
        for line in msec.group(1).strip().split('\n'):
            m = re.match(r'^(.+?)\(BK\d+\):.*MA5=(\d+\.?\d*)\((\w+)\).*MA20=(\d+\.?\d*)\((\w+)\)', line)
            if m: sma[m.group(1).strip()] = {'ma5': float(m.group(2)), 'ma5_status': m.group(3),
                                              'ma20': float(m.group(4)), 'ma20_status': m.group(5)}
    data['sector_ma'] = sma

    # 中军行情
    msec2 = re.search(r'核心中军行情.*?\n\n(.*?)(?:\n\n日期:|\n\n全市场)', content, re.DOTALL)
    mid_caps = []
    if msec2:
        for line in msec2.group(1).strip().split('\n'):
            m = re.search(r'^(.+?)\((\d+)\): ([\d.]+) ([+\-][\d.]+)% 成交([\d.]+)亿', line)
            if m: mid_caps.append({'name': m.group(1), 'code': m.group(2), 'price': float(m.group(3)),
                                   'pct': float(m.group(4)), 'amount': float(m.group(5))})
    data['mid_caps'] = mid_caps

    # Top20
    tsec = re.search(r'全市场成交额Top20\n\n(.*?)(?:\n\n===)', content, re.DOTALL)
    top20 = []
    if tsec:
        for line in tsec.group(1).strip().split('\n'):
            m = re.search(r'\d+\. (.+?)\((\d+)\): ([+\-][\d.]+)% 成交([\d.]+)亿 总市值([\d.]+)亿', line)
            if m: top20.append({'name': m.group(1), 'code': m.group(2), 'pct': float(m.group(3)),
                                'amount': float(m.group(4)), 'market_cap': float(m.group(5))})
    data['top20'] = top20

    # 强势股池
    qsec = re.search(r'强势股总数: (\d+)\n\n-+\n(.*?)(?:\n\n日期:|\n\n===|$)', content, re.DOTALL)
    qs = []
    if qsec:
        for line in qsec.group(2).strip().split('\n'):
            parts = line.split()
            if len(parts) >= 9:
                try:
                    qs.append({'name': parts[1], 'code': parts[2], 'pct': float(parts[3].replace('%','')),
                               'turnover': float(parts[4].replace('%','')), 'amount': float(parts[5].replace('亿','')),
                               'lb': float(parts[6]), 'nh': int(parts[7]), 'trend_score': float(parts[8])})
                except: pass
    data['qs_stocks'] = qs
    return data

# -------------------- 评分与角色 --------------------
def get_policy(name):
    for k,v in POLICY_HINTS.items():
        if k in name: return v
    return 3

def calc_sector_score(concept, data):
    name = concept.get('name','')
    if not name: return 0
    policy = get_policy(name)
    pct = concept.get('pct',0)
    money = 5 if pct>5 else (3 if pct>2 else 1)
    limit_cnt = data.get('limit_by_sector',{}).get(name,0)
    if not limit_cnt:
        for sn,c in data.get('limit_by_sector',{}).items():
            if name in sn or sn in name:
                limit_cnt = c; break
    limit_score = 5 if limit_cnt>=10 else (3 if limit_cnt>=5 else 1)
    seal = 0
    leader = concept.get('leader','')
    for st in data.get('limit_stocks',[]):
        if st['name']==leader: seal=st['seal_amount']; break
    seal_score = 5 if seal>5 else (3 if seal>1 else 1)
    mids = []
    for key,names in MID_CAP_MAP.items():
        if key in name:
            for n in names:
                for st in data.get('top20',[])+data.get('mid_caps',[]):
                    if st['name']==n: mids.append(st)
    if mids:
        avg = sum(s['pct'] for s in mids)/len(mids)
        mid_score = 5 if avg>=9.8 else (3 if avg>5 else 2)
    else: mid_score=1
    total = policy*0.2 + money*0.3 + limit_score*0.2 + seal_score*0.15 + mid_score*0.15
    return round(total,2)

def get_sector_mid_trend(name, data):
    ma = data.get('sector_ma',{})
    if name in ma:
        info = ma[name]; return info.get('ma5_status')=='已跌破', info.get('ma20_status')=='已跌破'
    for k,v in ma.items():
        if name in k or k in name:
            return v.get('ma5_status')=='已跌破', v.get('ma20_status')=='已跌破'
    return False, False

def identify_roles(concept_name, data):
    limit_stocks = data.get('limit_stocks',[])
    top20 = data.get('top20',[])
    mid_caps = data.get('mid_caps',[])
    qs = data.get('qs_stocks',[])
    kw = [concept_name[:4], concept_name.replace('概念','')]
    def related(n): return any(k in n for k in kw)

    rel_limit = [s for s in limit_stocks if related(s['name'])]
    rel_qs = [s for s in qs if related(s['name'])]

    # 中军（code去重）
    seen = set()
    mids = []
    for obj in top20 + mid_caps:
        code = obj.get('code','')
        if related(obj['name']) and obj.get('market_cap',0)>200 and code not in seen:
            mids.append(obj); seen.add(code)
    if not mids:
        for key,names in MID_CAP_MAP.items():
            if key in concept_name:
                for n in names:
                    for obj in top20+mid_caps:
                        if obj['name']==n and obj.get('code','') not in seen:
                            mids.append(obj); seen.add(obj.get('code',''))
                break
    mids = mids[:2]

    # 连板先锋
    def score_lb(st):
        t = st['turnover']
        ts = 10 if 3<=t<=7 else (7 if 7<t<=15 else (3 if t<3 else 2))
        try:
            h,m = map(int, st['first_time'].split(':'))
            mins = h*60+m
        except: mins = 999
        if mins<=570: ti=10
        elif mins<=600: ti=9
        elif mins<=630: ti=7
        elif mins<=690: ti=5
        else: ti=2
        sr = st['seal_amount']/st['amount'] if st['amount']>0 else 0
        se = 9 if sr>3 else (7 if sr>2 else (5 if sr>1 else 3))
        return ts*0.4 + ti*0.35 + se*0.25, st
    lianban = None
    if rel_limit:
        scored = [score_lb(s) for s in rel_limit]
        scored.sort(key=lambda x: x[0], reverse=True)
        lianban = scored[0][1]

    # 趋势先锋
    cands = [q for q in rel_qs if q.get('lb',0)>=1.5]
    valid = []
    for q in cands:
        lb_cnt = 0
        for ls in limit_stocks:
            if ls['code']==q['code']: lb_cnt = ls['lianban']; break
        if lb_cnt<=2: valid.append(q)
    trend = None
    if valid:
        valid.sort(key=lambda x: x.get('trend_score',0), reverse=True)
        trend = valid[0]
    return {'mid_cap': mids, 'lianban_pioneer': lianban, 'trend_pioneer': trend}

# -------------------- 主线与锚点 --------------------
def update_candidate_scores(candidates, data):
    scores = load_json(CANDIDATE_SCORES_FILE)
    today = data['date']
    for cand in candidates:
        name = cand['name']
        sc = calc_sector_score(cand, data)
        if name not in scores: scores[name] = []
        if not any(s['date']==today for s in scores[name]):
            scores[name].append({'date':today,'score':sc})
        scores[name] = scores[name][-10:]
    save_json(CANDIDATE_SCORES_FILE, scores)
    return scores

def get_main_from_anchor(a):
    if not a or 'main_line' not in a: return None,None,None,None
    m = a['main_line']
    return m.get('name'), m.get('stage'), m.get('last_score'), a.get('t_day')

def update_anchor(a, name, stage, score, t_day=None):
    a['main_line'] = {'name':name,'stage':stage,'last_score':score}
    if t_day: a['t_day'] = t_day
    if 'history' not in a: a['history'] = []
    today = t_day or a.get('t_day')
    if not any(h.get('date')==today and h.get('stage')==stage for h in a['history']):
        a['history'].append({'date':today,'main_line':name,'stage':stage,'score':score})
    save_json(GLOBAL_ANCHOR_FILE, a)

def check_confirmation(name, hist, data):
    if len(hist) < CONFIRM_DAYS: return False
    if all(s['score']>=MIN_SCORE_MAIN_LINE for s in hist[-CONFIRM_DAYS:]):
        b,_ = get_sector_mid_trend(name, data)
        if not b: return True
    return False

def check_switch(cname, chist, mname, mscore, data):
    if len(chist) < SWITCH_DAYS: return False
    if all(s['score']>mscore for s in chist[-SWITCH_DAYS:]):
        cb,_ = get_sector_mid_trend(cname, data)
        mb,_ = get_sector_mid_trend(mname, data)
        if not cb and mb: return True
    return False

def determine_main_lines(anchor, data):
    today = data['date']
    mname, mstage, mscore, _ = get_main_from_anchor(anchor)
    concepts = data.get('concepts',[])
    cands = [(c['name'], calc_sector_score(c, data)) for c in concepts]
    cands.sort(key=lambda x: x[1], reverse=True)
    cands = [c for c in cands if not any(e in c[0] for e in EXCLUDE_CONCEPTS)]
    scores = update_candidate_scores(concepts, data)

    if not mname or mstage == 'E':
        for cn,_ in cands:
            hist = scores.get(cn,[])
            if check_confirmation(cn, hist, data):
                ns = calc_sector_score({'name': cn, 'pct': next((c['pct'] for c in concepts if c['name']==cn),0)}, data)
                update_anchor(anchor, cn, 'C', ns, today)
                mname, mstage, mscore = cn, 'C', ns
                break
        else:
            return [], "无确认主线（寻找中）", None, None

    main_today_score = next((s for n,s in cands if n==mname), mscore)
    if not any(c['name']==mname for c in concepts):
        hist = scores.get(mname,[])
        if len(hist)>=DECLINE_DAYS and all(s['score']<3.0 for s in hist[-DECLINE_DAYS:]):
            update_anchor(anchor, mname, 'E', main_today_score)
            return determine_main_lines(anchor, data)
        roles = identify_roles(mname, data)
        return [{'name':mname,'score':main_today_score,'stage':mstage,'roles':roles}], f"主线：{mname}（{mstage}）", mname, mstage

    b5, b20 = get_sector_mid_trend(mname, data)

    if mstage == 'C':
        ns = '1G-1' if main_today_score>=4.5 and not b5 else 'C'
    elif 'G' in mstage:
        if b5:
            num = int(mstage.split('-')[0][0])
            ns = f'{num}D-1'
        else:
            parts = mstage.split('-')
            nd = int(parts[1])+1 if len(parts)>1 else 1
            ns = f"{parts[0]}-{nd}"
    elif 'D' in mstage:
        if not b5 and main_today_score>=4.0:
            num = int(mstage.split('-')[0][0])+1
            ns = f'{num}G-1'
        else:
            parts = mstage.split('-')
            nd = int(parts[1])+1
            ns = f"{parts[0]}-{nd}"
    else:
        ns = mstage

    if main_today_score<3.0 and b20:
        ns = 'E'
    update_anchor(anchor, mname, ns, main_today_score)

    for cn,_ in cands:
        if cn==mname: continue
        hist = scores.get(cn,[])
        if check_switch(cn, hist, mname, mscore, data):
            ns2 = calc_sector_score({'name':cn,'pct': next((c['pct'] for c in concepts if c['name']==cn),0)}, data)
            update_anchor(anchor, cn, 'C', ns2, today)
            mname, ns = cn, 'C'
            break

    out = []
    roles = identify_roles(mname, data)
    out.append({'name':mname,'score':main_today_score,'stage':ns,'roles':roles})
    for cn,sc in cands[:3]:
        if cn!=mname and sc>=3.0:
            out.append({'name':cn,'score':sc,'stage':'候选','roles':identify_roles(cn, data)})
    return out, f"主线：{mname}（{ns}）", mname, ns

# -------------------- 策略输出 --------------------
def generate_strategy(data, anchor):
    date_str = data['date']
    next_date = (datetime.strptime(date_str,'%Y%m%d')+timedelta(days=1)).strftime('%Y%m%d')
    # ---------- 关键修复：两市成交额 ----------
    sh_amt = data.get('sh_amount', 0)
    sz_amt = data.get('sz_amount', 0)
    total_amt = sh_amt + sz_amt
    print(f"[调试] 上证成交额: {sh_amt}亿, 深证成交额: {sz_amt}亿, 合计: {total_amt}亿")
    # -----------------------------------------
    sh, m20, mlb = data.get('sh_index',0), data.get('ma20',0), data.get('max_lianban',0)

    if sh>m20 and total_amt>22000 and mlb>5: env, max_cang = 'S',4
    elif sh>m20 and total_amt>=15000: env, max_cang = 'A',3
    else: env, max_cang = 'B',2

    mlines, main_msg, mname, mstage = determine_main_lines(anchor, data)

    lines = []
    lines.append(f"# 豆包模式 · 自动盘前策略（{date_str} 复盘 -> {next_date}）")
    lines.append(f"\n> **环境等级**：{env}级 | 总仓位上限：仓{max_cang} | 生成时间：{datetime.now().strftime('%H:%M:%S')}")
    lines.append("\n## 1. 大盘状态")
    lines.append(f"- 上证：{sh:.2f}（{data.get('sh_pct',0):+.2f}%），成交{sh_amt:.0f}亿")
    lines.append(f"- 两市成交：{total_amt:.0f}亿")
    if 'up_count' in data: lines.append(f"- 涨跌家数：{data['up_count']}涨 / {data['down_count']}跌")
    lines.append(f"- 20日线：{m20:.2f}（{'站上' if sh>m20 else '跌破'}）")
    lines.append("\n## 2. 情绪周期")
    lines.append(f"- 涨停{data.get('limit_total',0)} | 跌停{data.get('dieting_total',0)} | 炸板{data.get('zhaban_total',0)}")
    lines.append(f"- 最高连板：{mlb}连板")

    if CURRENT_HOLDINGS:
        lines.append("\n## 当前持仓处理")
        for s,p in CURRENT_HOLDINGS.items():
            if mname=='算力/CPO' and mstage=='E':
                lines.append(f"- **{s}（{p}成）：主线已退潮（E），建议清仓**")
            else:
                lines.append(f"- {s}（{p}成）：根据主线状态决定去留")

    lines.append("\n## 3. 主线评估与角色定位")
    lines.append(main_msg)
    for ml in mlines:
        sym = "[OK]" if ml['score']>=4.5 else ("[WATCH]" if ml['score']>=4.0 else "[WARN]")
        lines.append(f"\n### {sym} {ml['name']}（{ml['score']}分，阶段：{ml['stage']}）")
        roles = ml.get('roles',{})
        if ml['stage']=='C': lines.append("- 启动日，等待确认")
        elif 'G' in ml['stage']: lines.append("- 主升期，持有不加仓")
        elif 'D' in ml['stage']: lines.append("- 分歧期，观察活口")
        elif ml['stage']=='E': lines.append("- **退潮期，不参与，清仓相关标的**")
        else: lines.append("- 候选方向")
        if roles:
            mid_cap = roles.get('mid_cap',[])
            lb = roles.get('lianban_pioneer')
            tr = roles.get('trend_pioneer')
            if mid_cap:
                parts = [f"{m['name']}(成交{m.get('amount',0):.0f}亿)" for m in mid_cap]
                lines.append(f"- 核心中军：{', '.join(parts)}")
            if tr: lines.append(f"- 趋势先锋：{tr['name']}(趋势评分{tr.get('trend_score',0):.1f}，量比{tr.get('lb',1):.1f})")
            if lb: lines.append(f"- 连板先锋：{lb['name']}(封板{lb['first_time']}，换手{lb['turnover']}%，封单{lb['seal_amount']:.2f}亿)")

    lines.append("\n## 4. 明日执行清单")
    lines.append(f"- 总仓位上限：{max_cang*10}%")
    for ml in mlines:
        if ml['stage']=='C':
            lines.append(f"\n### {ml['name']}（C日->等待确认）")
            lines.append("- 确认信号：板块涨停>=10家、中军大涨>7% -> 买点C类型B")
        elif ml['stage'] in ('1G-1','2G-1','3G-1'):
            lines.append(f"\n### {ml['name']}（弱转强确认日）")
            lines.append("- 可执行D2/D3买点，仓位仓2-仓3")
    if not any(ml['stage'] in ('C','1G-1','2G-1','3G-1') for ml in mlines):
        lines.append("\n执行清单为空（无符合买点的方向）")

    lines.append(f"\n---\n*本策略由豆包模式自动生成 v5.6*")
    return '\n'.join(lines)

def main():
    replay = find_latest_replay()
    print(f"[读取] {replay}")
    data = parse_replay(replay)
    print("[解析完成]")
    today = data['date']
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip()==today:
                print(f"[跳过] 今天（{today}）的策略已生成。"); return

    anchor = load_json(GLOBAL_ANCHOR_FILE)
    if not anchor:
        anchor = {"t_day":None,"main_line":{"name":None,"stage":"E","last_score":0},"history":[]}
        save_json(GLOBAL_ANCHOR_FILE, anchor)

    strategy = generate_strategy(data, anchor)
    next_date = (datetime.strptime(today,'%Y%m%d')+timedelta(days=1)).strftime('%Y%m%d')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file,'w',encoding='utf-8') as f: f.write(strategy)
    print(f"[策略已保存] {out_file}")
    with open(LOCK_FILE,'w',encoding='utf-8') as f: f.write(today)
    print(strategy[:800])

if __name__ == '__main__':
    main()