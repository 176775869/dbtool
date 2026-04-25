# coding=utf-8
"""
保存每日摘要到 history.json，并生成昨日对比（含成交额环比）
"""
import json
import os
from datetime import datetime, timedelta

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def extract_today_summary(date_str):
    """从当天已生成的数据文件中提取关键指标"""
    summary = {'date': date_str}

    # 从涨停数据提取涨停总数和最高连板
    limit_file = get_output_path(f'limit_up_data_{date_str}.txt')
    if os.path.exists(limit_file):
        with open(limit_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('涨停总数:'):
                    try:
                        summary['limit_total'] = int(line.split(':')[1].strip())
                    except: pass
                elif line.startswith('最高连板:'):
                    try:
                        summary['max_limit_height'] = int(line.split(':')[1].strip().replace('连板',''))
                    except: pass

    # 从概念板块涨幅第一中提取最强方向和涨幅
    sector_file = get_output_path(f'sector_data_{date_str}.txt')
    if os.path.exists(sector_file):
        with open(sector_file, 'r', encoding='utf-8') as f:
            content = f.read()
            found_header = False
            for line in content.split('\n'):
                if '概念板块涨幅前' in line:
                    found_header = True
                    continue
                if not found_header:
                    continue
                line = line.strip()
                if not line or line.startswith('-') or line.startswith('==='):
                    continue
                if ':' in line and '%' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        summary['top_concept'] = parts[0].strip()
                        value_str = parts[1].strip().split(' ')[0].replace('%','').replace('+','')
                        try:
                            summary['top_concept_change'] = float(value_str)
                        except: pass
                    break

    # 从指数数据提取上证成交额
    index_file = get_output_path(f'index_data_{date_str}.txt')
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.split('\n'):
                if '上证指数' in line and '成交额' in line:
                    amount_str = line.split('成交额')[1].strip().replace('亿','')
                    try:
                        summary['sh_amount'] = float(amount_str)
                    except: pass
                    break

    return summary

def generate_comparison(today, yesterday):
    """生成昨日对比段落"""
    lines = ["\n=== 昨日数据对比 ==="]
    if yesterday:
        limit_diff = today.get('limit_total', 0) - yesterday.get('limit_total', 0)
        lines.append(f"涨停数: 昨日{yesterday.get('limit_total', '?')} → 今日{today.get('limit_total', '?')} ({limit_diff:+d})")
        height_diff = today.get('max_limit_height', 0) - yesterday.get('max_limit_height', 0)
        lines.append(f"连板高度: 昨日{yesterday.get('max_limit_height', '?')} → 今日{today.get('max_limit_height', '?')} ({height_diff:+d})")
        if 'sh_amount' in today and 'sh_amount' in yesterday:
            amount_diff = today['sh_amount'] - yesterday['sh_amount']
            lines.append(f"上证成交额: 昨日{yesterday['sh_amount']:.0f}亿 → 今日{today['sh_amount']:.0f}亿 ({amount_diff:+.0f}亿)")
        lines.append(f"昨日最强概念: {yesterday.get('top_concept', '?')} {yesterday.get('top_concept_change', 0):+.2f}%")
        lines.append(f"今日最强概念: {today.get('top_concept', '?')} {today.get('top_concept_change', 0):+.2f}%")
    else:
        lines.append("（暂无昨日数据，首次运行）")
    return '\n'.join(lines)

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    today_summary = extract_today_summary(date_str)

    history_file = get_output_path('history.json')
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

    yesterday_summary = next((h for h in history if h['date'] == yesterday_str), None)

    if not any(h['date'] == date_str for h in history):
        history.append(today_summary)
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    comparison = generate_comparison(today_summary, yesterday_summary)
    fn = get_output_path(f'history_compare_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(comparison)
    print(f"✅ 历史对比已保存至 {fn}")