# coding=utf-8
"""
获取板块行情数据（行业板块 + 概念板块，含涨跌家数）
输出：sector_data_YYYYMMDD.txt
"""
import requests
import json
import time
from datetime import datetime
import os

def get_output_path(filename):
    """获取文件保存路径，放在 py 文件夹内"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def fetch_eastmoney(url, name="接口"):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(1, 8):
        try:
            print(f"[{name}] 第{attempt}次请求...")
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'
            text = resp.text

            # 兼容 JSONP 和纯 JSON 两种返回格式
            if '(' in text and ')' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                json_str = text[s:e]
            else:
                json_str = text

            data = json.loads(json_str)
            if data.get('data') and data['data'].get('diff') is not None:
                return data['data']['diff']
            else:
                print(f"[{name}] 数据为空，重试...")
                time.sleep(2)
        except Exception as e:
            print(f"[{name}] 失败: {str(e)[:50]}")
            time.sleep(2)
    return []

def get_all_industry_sectors():
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:2&pn=1&pz=10000&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&"
        "fields=f2,f3,f4,f6,f12,f14,f104,f105,f128,f140"
    )
    return fetch_eastmoney(url, "行业板块")

def get_all_concept_sectors():
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:3&pn=1&pz=10000&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&"
        "fields=f2,f3,f4,f6,f12,f14,f104,f105,f128,f140"
    )
    return fetch_eastmoney(url, "概念板块")

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')

    print("获取行业板块行情...")
    industry_list = get_all_industry_sectors()
    print(f"行业板块数量: {len(industry_list)}")

    time.sleep(1.5)

    print("获取概念板块行情...")
    concept_list = get_all_concept_sectors()
    print(f"概念板块数量: {len(concept_list)}")

    filename = get_output_path(f'sector_data_{date_str}.txt')
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n")

        f.write("\n=== 行业板块涨幅前15 ===\n")
        industry_sorted = sorted(industry_list, key=lambda x: x.get('f3', 0), reverse=True)
        for item in industry_sorted[:15]:
            name = item.get('f14', '')
            change = item.get('f3', 0)
            amount = item.get('f6', 0) / 1e8 if item.get('f6') else 0
            leader = item.get('f128', '')
            up_count = item.get('f104', '?')
            down_count = item.get('f105', '?')
            f.write(f"{name}: {change:+.2f}% 成交{amount:.1f}亿 涨{up_count}/跌{down_count} 领涨:{leader}\n")

        f.write("\n=== 概念板块涨幅前20 ===\n")
        concept_sorted = sorted(concept_list, key=lambda x: x.get('f3', 0), reverse=True)
        for item in concept_sorted[:20]:
            name = item.get('f14', '')
            change = item.get('f3', 0)
            amount = item.get('f6', 0) / 1e8 if item.get('f6') else 0
            leader = item.get('f128', '')
            up_count = item.get('f104', '?')
            down_count = item.get('f105', '?')
            f.write(f"{name}: {change:+.2f}% 成交{amount:.1f}亿 涨{up_count}/跌{down_count} 领涨:{leader}\n")

    print(f"板块数据已保存至 {filename}")
    print("\n前5个概念板块预览:")
    for item in concept_sorted[:5]:
        print(f"  {item.get('f14','')}: {item.get('f3',0):+.2f}%")