# coding=utf-8
"""解析 replay_full_*.txt 数据包"""
import re

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

    # 深证
    m = re.search(r'深证成指: [\d.]+\D+([+\-][\d.]+)%\D+([\d.]+)亿', content)
    if not m:
        m = re.search(r'深证成指: ([\d.]+)，涨跌幅 ([+\-][\d.]+)%，成交额 ([\d.]+)亿', content)
    if m:
        try:
            if len(m.groups()) == 2:
                data['sz_amount'] = float(m.group(2))
            else:
                data['sz_amount'] = float(m.group(3))
        except:
            data['sz_amount'] = 0
    else:
        data['sz_amount'] = 0

    # 20日线
    m = re.search(r'上证20日均线: ([\d.]+)', content)
    if m: data['ma20'] = float(m.group(1))

    # 涨跌家数
    m = re.search(r'两市上涨家数: (\d+)，下跌家数: (\d+)', content)
    if m: data['up_count'], data['down_count'] = int(m.group(1)), int(m.group(2))

    # 涨停等
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
    con_sec = re.search(r'=== 概念板块涨幅前20 ===\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    concepts = []
    if con_sec:
        for line in con_sec.group(1).strip().split('\n'):
            if ': ' in line:
                name, rest = line.split(': ', 1)
                pm = re.search(r'([+\-][\d.]+)%', rest)
                am = re.search(r'成交([\d.]+)亿', rest)
                lm = re.search(r'领涨:(.+)', rest)
                if pm:
                    concepts.append({
                        'name': name.strip(), 'pct': float(pm.group(1)),
                        'amount': float(am.group(1)) if am else 0,
                        'leader': lm.group(1).strip() if lm else ''
                    })
    data['concepts'] = concepts

    # 板块涨停家数统计
    ssec = re.search(r'板块涨停家数统计\n-+\n(.*?)(?:\n\n日期:|$)', content, re.DOTALL)
    limit_by_sector = {}
    if ssec:
        for line in ssec.group(1).strip().split('\n'):
            m = re.match(r'^(.+?):\s*(\d+)只涨停', line.strip())
            if m: limit_by_sector[m.group(1).strip()] = int(m.group(2))
    data['limit_by_sector'] = limit_by_sector

    # 板块均线
    msec = re.search(r'板块均线状态.*?\n\n((?:.+\n)+?)(?:\n日期:|$)', content, re.DOTALL)
    sector_ma = {}
    if msec:
        for line in msec.group(1).strip().split('\n'):
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
    msec2 = re.search(r'核心中军行情.*?\n\n(.*?)(?:\n\n日期:|\n\n全市场)', content, re.DOTALL)
    mid_caps = []
    if msec2:
        for line in msec2.group(1).strip().split('\n'):
            m = re.search(r'^(.+?)\((\d+)\): ([\d.]+) ([+\-][\d.]+)% 成交([\d.]+)亿', line)
            if m:
                mid_caps.append({
                    'name': m.group(1), 'code': m.group(2),
                    'price': float(m.group(3)), 'pct': float(m.group(4)),
                    'amount': float(m.group(5))
                })
    data['mid_caps'] = mid_caps

    # Top20
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

    # 强势股池
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