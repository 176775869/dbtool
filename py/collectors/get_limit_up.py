# coding=utf-8
"""
涨停板完整数据（修复反爬版）
接口: getTopicZTPool, 域名 push2ex.eastmoney.com
"""
import requests
import json
import time
import os
from datetime import datetime
from collections import Counter

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def format_time(raw):
    if not raw or raw in ('-', '', 0, '0', None):
        return '--'
    try:
        t = str(int(raw)).zfill(6)
        return f"{t[:2]}:{t[2:4]}:{t[4:6]}"
    except:
        return str(raw)

def format_zttj(obj):
    if not obj or not isinstance(obj, dict):
        return ''
    d, c = obj.get('days', 0), obj.get('ct', 0)
    return f"{d}天{c}板" if d > 0 and c > 0 else ''

def fetch_all(date_str):
    all_items = []
    page, size = 0, 100
    while True:
        url = (
            f"https://push2ex.eastmoney.com/getTopicZTPool?"
            f"cb=callbackdata5360762&ut=7eea3edcaed734bea9cbfc24409ed989&"
            f"dpt=wz.ztzt&Pageindex={page}&pagesize={size}&"
            f"sort=fbt%3Aasc&date={date_str}&_={int(time.time()*1000)}"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            # 【核心修复】将 Referer 从 https 改为 http，与浏览器真实访问行为一致
            'Referer': 'http://quote.eastmoney.com/ztb/detail'
        }
        print(f"请求涨停第{page+1}页...")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            if resp.status_code != 200 or not text:
                time.sleep(2)
                continue
            s = text.index('(') + 1
            e = text.rindex(')')
            data = json.loads(text[s:e])
            if data and 'data' in data:
                pool = data['data']
                items = pool.get('pool', [])
                total = pool.get('tc', pool.get('total', 0))
                all_items.extend(items)
                print(f"获取 {len(items)} 条, 累计 {len(all_items)}/{total}")
                if len(all_items) >= total:
                    break
                page += 1
                time.sleep(0.5)
            else:
                break
        except Exception as e:
            print(f"错误: {str(e)[:50]}, 重试...")
            time.sleep(2)
    return all_items

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    print("获取涨停板数据...")
    raw = fetch_all(date_str)

    if not raw:
        print("无数据")
        exit(1)

    zt = []
    for item in raw:
        try:
            seal_amt = float(item.get('fund', 0)) / 1e8
        except:
            seal_amt = 0

        zt.append({
            'code': item.get('c',''), 'name': item.get('n',''),
            'pct': round(float(item.get('zdp',0)), 1),
            'limit': int(item.get('lbc',0)),
            'zttj': format_zttj(item.get('zttj')),
            'fbt': format_time(item.get('fbt',0)),
            'lbt': format_time(item.get('lbt',0)),
            'amt': float(item.get('amount',0))/1e8,
            'seal_amt': seal_amt,
            'hbk': item.get('hybk', ''),
            'hs': float(item.get('hs',0))
        })

    normal_stocks = [z for z in zt if not (z['name'].startswith('N') or z['name'].startswith('C'))]
    new_stocks = [z for z in zt if (z['name'].startswith('N') or z['name'].startswith('C'))]
    normal_stocks.sort(key=lambda x: x['limit'], reverse=True)
    zt = normal_stocks + new_stocks

    sector_counter = Counter()
    for z in zt:
        sector = z.get('hbk', '')
        if sector and sector != '--':
            sector_counter[sector] += 1

    fn_sector_zt = get_output_path(f'sector_limit_up_{date_str}.txt')
    with open(fn_sector_zt, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n板块涨停家数统计\n\n")
        for sector, count in sector_counter.most_common():
            f.write(f"{sector}: {count}只涨停\n")
    print(f"[OK] 板块涨停统计已保存")

    total = len(zt)
    max_lt = max(z['limit'] for z in normal_stocks) if normal_stocks else 0
    top = [z for z in normal_stocks if z['limit'] == max_lt]

    fn = get_output_path(f'limit_up_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n涨停总数: {total}\n最高连板: {max_lt}连板\n")
        if top:
            f.write(f"最高连板股: {', '.join(s['name'] for s in top)}\n")
        f.write(f"\n{'序号':<4}{'名称':<10}{'代码':<8}{'涨幅':<8}{'连板':<4}{'类型':<10}{'首封':<10}{'最终':<10}{'换手':<8}{'成交':<10}{'封单额':<10}\n")
        f.write("-" * 105 + "\n")
        for i, z in enumerate(zt, 1):
            seal_str = f"{z['seal_amt']:.2f}亿" if z['seal_amt'] > 0 else '--'
            f.write(f"{i:<4}{z['name']:<10}{z['code']:<8}{z['pct']:>6.1f}%{z['limit']:>3}板{z['zttj']:<10}{z['fbt']:<10}{z['lbt']:<10}{z['hs']:>6.2f}%{z['amt']:>8.2f}亿  {seal_str}\n")

    print(f"[OK] 涨停数据已保存, 共{total}只, 最高{max_lt}连板")
    for s in top:
        print(f"  {s['name']} {s['limit']}连板 {s['zttj']} 首封{s['fbt']}")