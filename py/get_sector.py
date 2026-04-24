# coding=utf-8
"""
获取板块行情数据（增强日志版）
"""
import requests
import json
import time
import os
from datetime import datetime

def get_output_path(filename):
    """获取文件保存路径：与脚本同目录，放在 py 文件夹内"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    py_dir = os.path.join(script_dir, '..', 'py')  # 合并到上层的 py 目录
    os.makedirs(py_dir, exist_ok=True)
    return os.path.join(py_dir, filename)

def fetch_eastmoney(url, name="接口"):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    for attempt in range(1, 8):   # 最多重试7次
        try:
            print(f"[{name}] 第{attempt}次尝试，URL: {url[:120]}...")
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"[{name}] 响应状态码: {resp.status_code}")
            print(f"[{name}] 响应内容前200字符: {resp.text[:200]}")
            
            # 如果是 jsonp 格式，提取 json 部分
            text = resp.text
            if 'jQuery' in text or 'callback' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                json_str = text[s:e]
                data = json.loads(json_str)
            else:
                data = json.loads(text)
            
            if data.get('data') and data['data'].get('diff'):
                print(f"[{name}] 成功获取，数据条数: {len(data['data']['diff'])}")
                return data['data']['diff']
            else:
                print(f"[{name}] 返回数据为空或格式异常，data字段: {data.get('data')}")
                time.sleep(2)
        except requests.exceptions.ConnectionError as e:
            print(f"[{name}] 连接错误 (可能是IP被临时限制): {e}")
            print(f"[{name}] 等待30秒后重试...")
            time.sleep(30)
        except Exception as e:
            print(f"[{name}] 解析失败: {e}")
            time.sleep(3)
    return []

def get_all_industry_sectors():
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:2&pn=1&pz=10000&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&"
        "fields=f2,f3,f4,f6,f12,f14,f128,f140"
    )
    return fetch_eastmoney(url, "行业板块")

def get_all_concept_sectors():
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:3&pn=1&pz=10000&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&"
        "fields=f2,f3,f4,f6,f12,f14,f128,f140"
    )
    return fetch_eastmoney(url, "概念板块")

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    
    print("=" * 50)
    print("开始获取行业板块...")
    industry_list = get_all_industry_sectors()
    print(f"行业板块获取完成，数量: {len(industry_list)}")
    
    time.sleep(1.5)
    
    print("=" * 50)
    print("开始获取概念板块...")
    concept_list = get_all_concept_sectors()
    print(f"概念板块获取完成，数量: {len(concept_list)}")
    
    # 保存
    filename = get_output_path(f"sector_data_{date_str}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n\n")
        f.write("=== 行业板块涨幅前15 ===\n")
        for item in sorted(industry_list, key=lambda x: x.get('f3', 0), reverse=True)[:15]:
            f.write(f"{item['f14']}: {item['f3']:+.2f}% 成交{item['f6']/1e8:.1f}亿 领涨:{item.get('f128','')}\n")
        
        f.write("\n=== 概念板块涨幅前20 ===\n")
        for item in sorted(concept_list, key=lambda x: x.get('f3', 0), reverse=True)[:20]:
            f.write(f"{item['f14']}: {item['f3']:+.2f}% 成交{item['f6']/1e8:.1f}亿 领涨:{item.get('f128','')}\n")
    
    print(f"文件已保存至 {filename}")