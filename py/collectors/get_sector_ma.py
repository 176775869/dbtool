# coding=utf-8
"""获取热门板块的均线数据（修复版）"""
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
            return json.loads(text)
        except Exception as e:
            print(f"  请求失败，重试 {attempt+1}: {str(e)[:80]}")
            time.sleep(2)
    return None

def auto_discover_sectors(date_str):
    """获取涨幅前5的概念板块"""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "cb=cb&fid=f62&po=1&pz=5&pn=1&np=1&fltt=2&invt=2"
        "&ut=8dec03ba335b81bf4ebdf7b29ec27d15"
        "&fs=m:90+t:3"
        "&fields=f12,f14"
    )
    data = fetch_json(url)
    if not data or 'data' not in data or not data['data'].get('diff'):
        return []

    codes = []
    for item in data['data']['diff']:
        code = item.get('f12', '')
        name = item.get('f14', '')
        if code:
            codes.append((code, name))
    return codes

def _inject_tracking_codes():
    try:
        from get_sector import extract_tracking_directions, filter_tracking_sectors
        import requests, json
        tracking_dirs = extract_tracking_directions()
        if not tracking_dirs:
            return []
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1", "pz": "500", "po": "1", "np": "1",
            "ut": "8dec03ba335b81bf4ebdf7b29ec27d15",
            "fltt": "2", "invt": "2",
            "fid": "f3", "fs": "m:90+t:3",
            "fields": "f12,f14"
        }
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            s = text.index('(') + 1
            e = text.rindex(')')
            data = json.loads(text[s:e])
            all_sectors = data.get('data', {}).get('diff', [])
            return filter_tracking_sectors(all_sectors, tracking_dirs)
    except Exception as e:
        print(f"动态注入失败: {e}")
    return []

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