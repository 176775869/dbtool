# coding=utf-8
"""
获取板块行情数据（行业板块 + 概念板块）
概念板块增加涨跌比 + 主力资金净流入
行业板块增加主力资金净流入
"""
import requests
import json
import time
import os
from datetime import datetime

def get_output_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def fetch_concept_sectors():
    """获取概念板块数据"""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "cb=cb&fid=f62&po=1&pz=10000&pn=1&np=1&fltt=2&invt=2"
        "&ut=8dec03ba335b81bf4ebdf7b29ec27d15"
        "&fs=m:90+t:3"
        "&fields=f12,f14,f2,f3,f4,f6,f62,f128,f104,f105"
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(5):
        try:
            print(f"[概念板块] 第{attempt+1}次请求...")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
            if '(' in text and ')' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                text = text[s:e]
            data = json.loads(text)
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
            else:
                print(f"[概念板块] 数据为空，重试...")
                time.sleep(2)
        except Exception as e:
            print(f"[概念板块] 失败: {str(e)[:50]}")
            time.sleep(2)
    return []

def fetch_industry_sectors():
    """获取行业板块数据"""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "np=1&fltt=1&invt=2&cb=cb"
        "&fs=m:90+t:2+f:!50"
        "&fields=f12,f14,f2,f3,f4,f6,f20,f104,f105,f128,f140,f62"
        "&fid=f3&pn=1&pz=10000&po=1&dect=1"
        "&ut=fa5fd1943c7b386f172d6893dbfba10b"
    )
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(5):
        try:
            print(f"[行业板块] 第{attempt+1}次请求...")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text
            if '(' in text and ')' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                text = text[s:e]
            data = json.loads(text)
            if data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
            else:
                print(f"[行业板块] 数据为空，重试...")
                time.sleep(2)
        except Exception as e:
            print(f"[行业板块] 失败: {str(e)[:50]}")
            time.sleep(2)
    return []

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')

    print("获取行业板块行情...")
    industry_list = fetch_industry_sectors()
    print(f"行业板块数量: {len(industry_list)}")

    time.sleep(1)

    print("获取概念板块行情...")
    concept_list = fetch_concept_sectors()
    print(f"概念板块数量: {len(concept_list)}")

    filename = get_output_path(f'sector_data_{date_str}.txt')
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n")

        # ---- 行业板块 ----
        f.write("\n=== 行业板块涨幅前15 ===\n")
        industry_sorted = sorted(industry_list, key=lambda x: float(x.get('f3', 0)), reverse=True)
        for item in industry_sorted[:15]:
            name = item.get('f14', '')
            change = float(item.get('f3', 0))
            amount = float(item.get('f6', 0)) / 1e8 if item.get('f6', '') != '' else 0
            leader = item.get('f128', '')
            up_count = item.get('f104', '?')
            down_count = item.get('f105', '?')
            net_inflow = float(item.get('f62', 0) or 0) / 1e8
            f.write(f"{name}: {change:+.2f}% 成交{amount:.1f}亿 涨{up_count}/跌{down_count} 主力净流入{net_inflow:.2f}亿 领涨:{leader}\n")

        # ---- 概念板块 ----
        f.write("\n=== 概念板块涨幅前20 ===\n")
        concept_sorted = sorted(concept_list, key=lambda x: float(x.get('f3', 0)), reverse=True)
        for item in concept_sorted[:20]:
            name = item.get('f14', '')
            change = float(item.get('f3', 0))
            amount = float(item.get('f6', 0)) / 1e8 if item.get('f6', '') != '' else 0
            leader = item.get('f128', '')
            up_count = item.get('f104', '?')
            down_count = item.get('f105', '?')
            net_inflow = float(item.get('f62', 0) or 0) / 1e8
            f.write(f"{name}: {change:+.2f}% 成交{amount:.1f}亿 涨{up_count}/跌{down_count} 主力净流入{net_inflow:.2f}亿 领涨:{leader}\n")

    print(f"板块数据已保存至 {filename}")
    if concept_sorted:
        print("\n前5个概念板块预览:")
        for item in concept_sorted[:5]:
            name = item.get('f14', '')
            change = float(item.get('f3', 0))
            print(f"  {name}: {change:+.2f}%")