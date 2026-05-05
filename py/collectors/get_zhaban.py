# coding=utf-8
"""
获取炸板股池数据（修正版）
接口: getTopicZBPool, 域名 push2ex.eastmoney.com, dpt=wz.ztzt (炸板池)
"""
import requests
import json
import time
import os
from datetime import datetime

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
            f"https://push2ex.eastmoney.com/getTopicZBPool?"
            f"cb=callbackdata9664180&ut=7eea3edcaed734bea9cbfc24409ed989&"
            f"dpt=wz.ztzt&Pageindex={page}&pagesize={size}&"
            f"sort=fbt%3Aasc&date={date_str}&_={int(time.time()*1000)}"
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/ztb/detail'
        }
        print(f"请求炸板第{page+1}页...")
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
    print("获取炸板数据...")
    raw = fetch_all(date_str)

    if not raw:
        print("今日无炸板股")
        fn = get_output_path(f'zhaban_data_{date_str}.txt')
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(f"日期: {date_str}\n炸板总数: 0\n炸板率: 0%\n")
        exit(0)

    zb = []
    for item in raw:
        zb.append({
            'code': item.get('c',''), 'name': item.get('n',''),
            'pct': round(float(item.get('zdp',0)), 1),
            'fbt': format_time(item.get('fbt',0)),
            'lbt': format_time(item.get('lbt',0)),
            'amt': float(item.get('amount',0))/1e8,
            'hbk': item.get('hybk', ''),
            'hs': float(item.get('hs',0))
        })

    total = len(zb)

    fn = get_output_path(f'zhaban_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n炸板总数: {total}\n\n")
        f.write(f"{'序号':<4}{'名称':<10}{'代码':<8}{'涨幅':<8}{'首封':<10}{'开板':<10}{'换手':<8}{'成交':<10}{'板块'}\n")
        f.write("-"*90 + "\n")
        for i, z in enumerate(zb, 1):
            f.write(f"{i:<4}{z['name']:<10}{z['code']:<8}{z['pct']:>6.1f}%{z['fbt']:<10}{z['lbt']:<10}{z['hs']:>6.2f}%{z['amt']:>8.2f}亿  {z['hbk']}\n")
    print(f"✅ 炸板数据已保存, 共{total}只")