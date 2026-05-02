import os, re, sys, json
from datetime import datetime
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def get_monitor_stocks():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    strategy_files = []
    for f in os.listdir(base_dir):
        if f.startswith('strategy_') and f.endswith('.md'):
            strategy_files.append(os.path.join(base_dir, f))
    if not strategy_files:
        return {}
    latest = max(strategy_files, key=os.path.getmtime)
    with open(latest, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'([\u4e00-\u9fa5]+)\s*\((\d{6})\)|(\d{6})'
    stocks = {}
    for match in re.finditer(pattern, content):
        name = match.group(1)
        code = match.group(2) or match.group(3)
        if code:
            market = '1' if code.startswith('6') else '0'
            stocks[code] = {'name': name, 'market': market, 'code': code}
    return stocks

def get_fenshi(code, market):
    secid = f'{market}.{code}'
    url = 'https://push2his.eastmoney.com/api/qt/stock/trends2/get'
    params = {
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
        'ut': '7eea3edcaed734bea9cbe4f9e2d12b5e', 'ndays': '1', 'iscr': '0',
        'secid': secid, '_': int(datetime.now().timestamp() * 1000)
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json().get('data', {})
        if data and data.get('trends'):
            return data['trends']
    except Exception as e:
        print(f'[分时] {code} 获取失败: {e}')
    return []

def get_pankou(code, market):
    secid = f'{market}.{code}'
    url = 'https://push2.eastmoney.com/api/qt/stock/get'
    params = {
        'fields': 'f43,f44,f45,f47,f48,f170',
        'ut': '7eea3edcaed734bea9cbe4f9e2d12b5e',
        'secid': secid, '_': int(datetime.now().timestamp() * 1000)
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json().get('data', {})
        if data:
            return {
                'price': data.get('f43', 0) / 100 if data.get('f43') else 0,
                'high': data.get('f44', 0) / 100 if data.get('f44') else 0,
                'low': data.get('f45', 0) / 100 if data.get('f45') else 0,
                'volume': data.get('f47', 0),
                'amount': data.get('f48', 0),
                'pct': data.get('f170', 0) / 100 if data.get('f170') else 0,
            }
    except Exception as e:
        print(f'[盘口] {code} 获取失败: {e}')
    return {}

def main():
    stocks = get_monitor_stocks()
    if not stocks:
        print('[订阅] 没有找到监控标的')
        return
    today = datetime.now().strftime('%Y%m%d')
    lines = [f'日期: {today}', '', '=== 盘中监控数据 ===']
    for code, info in stocks.items():
        name = info['name']
        market = info['market']
        print(f'[订阅] 获取 {name}({code}) 数据...')
        pankou = get_pankou(code, market)
        fenshi = get_fenshi(code, market)
        fenshi_tail = fenshi[-5:] if fenshi else []
        lines.append(f'\n{name}({code}):')
        if pankou:
            lines.append(f"  现价: {pankou.get('price', 0):.2f}")
            lines.append(f"  涨幅: {pankou.get('pct', 0):.2f}%")
            lines.append(f"  最高: {pankou.get('high', 0):.2f}")
            lines.append(f"  最低: {pankou.get('low', 0):.2f}")
            lines.append(f"  成交额: {pankou.get('amount', 0)}元")
        if fenshi_tail:
            lines.append(f"  近5分钟分时 (时间,开盘,收盘,最高,最低,成交量):")
            for point in fenshi_tail:
                lines.append(f"    {point}")
    content = '\n'.join(lines)
    output_path = os.path.join(DATA_DIR, f'subscription_{today}.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[订阅] 数据已保存到 {output_path}')

if __name__ == '__main__':
    main()
