# coding=utf-8
"""
获取全市场成交额Top20（复用已验证的接口）
"""
import requests
import json
import time
import os
from datetime import datetime

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def fetch_all_stocks():
    """用你req.py里已验证的接口拉取全市场数据"""
    url = (
        "http://23.push2.eastmoney.com/api/qt/clist/get?"
        "cb=jQuery112403461296577881501_1600744555568"
        "&pn=1&pz=5000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
        "&fltt=2&invt=2&fid=f6"  # 关键：按成交额排序
        "&fs=m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23"
        "&fields=f2,f3,f6,f8,f12,f14,f20,f21"
        "&_=1600744555569"
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            text = resp.text
            s = text.index('(') + 1
            e = text.rindex(')')
            data = json.loads(text[s:e])
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
        except Exception as e:
            print(f"  重试 {attempt+1}: {str(e)[:50]}")
            time.sleep(2)
    return []

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    
    print("获取全市场成交额数据...")
    items = fetch_all_stocks()
    
    if not items:
        print("获取失败")
        exit(1)
    
    # 取前20
    top20 = items[:20]
    
    lines = [f"日期: {date_str}", "全市场成交额Top20", ""]
    for i, item in enumerate(top20, 1):
        name = item.get('f14', '')
        code = item.get('f12', '')
        pct = float(item.get('f3', 0)) if item.get('f3', '-') != '-' else 0
        amount = float(item.get('f6', 0)) / 1e8
        market_cap = float(item.get('f20', 0)) / 1e8 if item.get('f20') not in ('-', '', None) else 0
        lines.append(f"{i}. {name}({code}): {pct:+.2f}% 成交{amount:.1f}亿 总市值{market_cap:.0f}亿")
    
    fn = get_output_path(f'top_amount_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"✅ 已保存至 {fn}")