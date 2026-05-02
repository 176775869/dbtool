"""
market_context_builder.py
抓取财联社电报，提炼当日产业催化摘要。
输出格式与其他数据采集脚本保持一致，方便 merge_replay 统一拼接。
输出到 py/data/market_context_YYYYMMDD.txt
"""
import requests
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def fetch_cls():
    """抓取财联社电报"""
    try:
        resp = requests.get(
            'https://www.cls.cn/api/telegraph/list?category=all&page=1&size=30',
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.cls.cn/telegraph'
            },
            timeout=10
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get('data', {}).get('list', [])
        titles = [item.get('title', '') for item in items if item.get('title')]
        return titles[:20]
    except Exception as e:
        print(f'[CLS error] {e}')
        return []


def filter_industry(news_list):
    """简要过滤：仅保留产业政策、重大技术、龙头公司相关"""
    keywords = [
        '政策', '部委', '国务院', '发改委', '工信部', '芯片', '半导体', '锂电',
        '新能源', '光伏', '储能', 'AI', '人工智能', '算力', 'CPO', '光模块',
        '军工', '航天', '卫星', '稀土', '碳酸锂', '涨价', '突破', '量产',
        '订单', '中标', '特高压', '机器人', '自动驾驶', '人形机器人',
        '低空经济', '商业航天', '固态电池', '钠离子', '量子', '核聚变'
    ]
    filtered = []
    for title in news_list:
        if any(kw in title for kw in keywords):
            filtered.append(title)
    return filtered[:15]


def main():
    today = datetime.now().strftime('%Y%m%d')
    now_str = datetime.now().strftime('%Y%m%d %H:%M:%S')

    # 抓取并过滤
    cls_titles = fetch_cls()
    unique_titles = list(dict.fromkeys(cls_titles))
    industry_titles = filter_industry(unique_titles)

    # ============ 格式保持与指数、涨停数据一致 ============
    lines = []
    lines.append(f"日期: {today}")
    lines.append(f"")
    lines.append(f"=== 产业催化电报 ===")
    if industry_titles:
        for i, title in enumerate(industry_titles, 1):
            lines.append(f"{i}. {title}")
    else:
        lines.append(f"今日暂无重大产业催化电报。")
    lines.append(f"")

    content = '\n'.join(lines)

    # 保存文件
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f'market_context_{today}.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[市场背景] 已保存到 {output_path}')


if __name__ == '__main__':
    main()