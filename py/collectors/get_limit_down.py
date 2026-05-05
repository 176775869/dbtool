# coding=utf-8
"""
获取跌停板完整数据（修正版）
接口: getTopicDTPool, 域名 push2ex.eastmoney.com
"""
import requests
import json
import time
import os
from datetime import datetime
from collections import Counter

def get_output_path(filename):
    return os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"), filename)

def format_time(raw):
    if not raw or raw in ('-', '', 0, '0', None):
        return '--'
    try:
        t = str(int(raw)).zfill(6)
        return f"{t[:2]}:{t[2:4]}:{t[4:6]}"
    except:
        return str(raw)

def fetch_all(date_str):
    all_items = []
    page, size = 0, 100
    while True:
        url = (
            f"https://push2ex.eastmoney.com/getTopicDTPool?"
            f"cb=callbackdata5654082&ut=7eea3edcaed734bea9cbfc24409ed989&"
            f"dpt=wz.ztzt&Pageindex={page}&pagesize={size}&"
            f"sort=fund%3Aasc&date={date_str}&_={int(time.time()*1000)}"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/ztb/detail'
        }
        print(f"请求跌停第{page+1}页...")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            text = resp.text
            if resp.status_code != 200 or not text:
                print(f"状态码 {resp.status_code}, 重试...")
                time.sleep(2)
                continue

            s = text.index('(') + 1
            e = text.rindex(')')
            data = json.loads(text[s:e])

            if not data or 'data' not in data:
                print("返回数据格式异常，重试...")
                time.sleep(2)
                continue

            pool_data = data['data']
            if not pool_data:
                break

            items = pool_data.get('pool', pool_data.get('diff', []))
            if not items:
                break

            total = pool_data.get('tc', pool_data.get('total', 0))
            all_items.extend(items)
            print(f"获取 {len(items)} 条, 累计 {len(all_items)}/{total}")

            if len(all_items) >= total:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"错误: {str(e)[:50]}, 重试...")
            time.sleep(2)
    return all_items

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    print("获取跌停板数据...")
    raw = fetch_all(date_str)

    if not raw:
        print("今日无跌停股")
        fn_down = get_output_path(f'limit_down_data_{date_str}.txt')
        with open(fn_down, 'w', encoding='utf-8') as f:
            f.write(f"日期: {date_str}\n跌停总数: 0\n\n今日无跌停股\n")
        fn_sector = get_output_path(f'sector_limit_down_{date_str}.txt')
        with open(fn_sector, 'w', encoding='utf-8') as f:
            f.write(f"日期: {date_str}\n板块跌停统计\n\n无跌停股\n")
        exit(0)

    dt = []
    for item in raw:
        dt.append({
            'code': item.get('c',''), 'name': item.get('n',''),
            'pct': round(float(item.get('zdp',0)), 1),
            'limit': int(item.get('lbc',0)),
            'fbt': format_time(item.get('fbt',0)),
            'lbt': format_time(item.get('lbt',0)),
            'amt': float(item.get('amount',0))/1e8,
            'hbk': item.get('hybk', ''),
            'hs': float(item.get('hs',0))
        })

    dt.sort(key=lambda x: x['pct'])

    sector_counter = Counter()
    for d in dt:
        sector = d.get('hbk', '')
        if sector and sector != '--':
            sector_counter[sector] += 1

    total = len(dt)

    fn = get_output_path(f'limit_down_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n跌停总数: {total}\n\n")
        f.write(f"{'序号':<4}{'名称':<10}{'代码':<8}{'跌幅':<8}{'连板':<4}{'首跌':<10}{'最终':<10}{'换手':<8}{'成交':<10}{'板块'}\n")
        f.write("-"*100 + "\n")
        for i, d in enumerate(dt, 1):
            f.write(f"{i:<4}{d['name']:<10}{d['code']:<8}{d['pct']:>6.1f}%{d['limit']:>3}板{d['fbt']:<10}{d['lbt']:<10}{d['hs']:>6.2f}%{d['amt']:>8.2f}亿  {d['hbk']}\n")

    fn_sector = get_output_path(f'sector_limit_down_{date_str}.txt')
    with open(fn_sector, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n板块跌停家数统计\n\n")
        for sector, count in sector_counter.most_common():
            f.write(f"{sector}: {count}只跌停\n")

    print(f"✅ 跌停数据已保存: {fn}")
    print(f"✅ 板块跌停统计已保存: {fn_sector}")
    print(f"跌停总数: {total}")