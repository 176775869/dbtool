# coding=utf-8
"""获取热门板块的均线数据（稳定版）"""
import sys, io
import requests
import json
import time
import os
from datetime import datetime, timedelta

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def fetch_json(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
            if text.startswith('jQuery') or '(' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                text = text[s:e]
            data = json.loads(text)
            return data
        except Exception as e:
            print(f"  请求失败，重试 {attempt+1}: {str(e)[:80]}")
            time.sleep(2)
    return None

def auto_discover_sectors(date_str):
    # 获取所有板块代码
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:2,m:90+t:3&pn=1&pz=10000&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&fields=f12,f14"
    )
    data = fetch_json(url)
    if not data or 'data' not in data or not data['data'].get('diff'):
        return []

    all_items = data['data']['diff']
    # 取当日涨幅前5的概念板块
    concept_url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:3&pn=1&pz=5&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&fields=f12,f14"
    )
    top5_data = fetch_json(concept_url)
    codes = []
    seen = set()
    if top5_data and 'data' in top5_data and top5_data['data'].get('diff'):
        for item in top5_data['data']['diff']:
            code = item.get('f12', '')
            name = item.get('f14', '')
            if code and code not in seen:
                codes.append((code, name))
                seen.add(code)

    # 补充关注列表中的板块（当前无历史则跳过）
    history_file = get_output_path('history.json')
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            watchlist = set()
            cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
            for record in history:
                if record['date'] >= cutoff:
                    if record.get('top_concept'): watchlist.add(record['top_concept'])
                    if record.get('top_industry'): watchlist.add(record['top_industry'])
            for item in all_items:
                if item.get('f14') in watchlist and item.get('f12') not in seen:
                    codes.append((item['f12'], item['f14']))
                    seen.add(item['f12'])
        except:
            pass

    return codes

def get_sector_ma(code, name):
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid=90.{code}&fields1=f1,f2,f3,f4,f5,f6&"
        f"fields2=f51,f52,f53,f54,f55,f56,f57&"
        f"klt=101&fqt=0&end=20500101&lmt=25&ut=bd1d9ddb04089700cf9c27f6f7426281"
    )
    data = fetch_json(url)
    if not data or 'data' not in data or not data['data'].get('klines'):
        return None

    closes = [float(line.split(',')[2]) for line in data['data']['klines'] if line]
    if len(closes) < 20:
        return None

    latest = closes[-1]
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20

    def status(price, ma):
        return "已跌破" if price < ma else "未破"

    return {
        'name': name, 'code': code,
        'latest': latest, 'ma5': round(ma5,2), 'ma10': round(ma10,2), 'ma20': round(ma20,2),
        'ma5_status': status(latest, ma5),
        'ma10_status': status(latest, ma10),
        'ma20_status': status(latest, ma20)
    }

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    print("自动发现板块...")
    sectors = auto_discover_sectors(date_str)
    print(f"找到 {len(sectors)} 个板块需要计算均线")

    if not sectors:
        print("未发现板块，跳过均线计算")
        fn = get_output_path(f'sector_ma_data_{date_str}.txt')
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(f"日期: {date_str}\n板块均线状态 (无数据)\n")
        exit(0)

    lines = [f"日期: {date_str}", "板块均线状态 (优先关注主线)", ""]
    for code, name in sectors:
        print(f"  计算 {name}({code}) 的均线...")
        ma = get_sector_ma(code, name)
        time.sleep(0.3)
        if ma:
            line = (f"{ma['name']}({ma['code']}): 收盘{ma['latest']:.2f}，"
                    f"MA5={ma['ma5']}({ma['ma5_status']})，"
                    f"MA10={ma['ma10']}({ma['ma10_status']})，"
                    f"MA20={ma['ma20']}({ma['ma20_status']})")
        else:
            line = f"{name}({code}): 均线数据不足（需积累20天）"
        lines.append(line)

    fn = get_output_path(f'sector_ma_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[完成] 板块均线数据已保存至 {fn}")