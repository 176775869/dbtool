# coding=utf-8
"""
获取动态中军池的实时行情 + 均线状态（基于本地历史数据计算，零反爬风险）
中军池自动构建，融合历史关注板块
"""
import requests
import json
import time
import os
import csv
from datetime import datetime, timedelta

# ==================== 数据老化清理（保留最近1年） ====================
def clean_old_data():
    """清理 price_history.csv 和 history.json 中超过1年的数据"""
    today = datetime.now()
    cutoff_date = (today - timedelta(days=365)).strftime('%Y%m%d')  # 格式：20250623
    print(f"🧹 开始数据清理，保留 {cutoff_date} 之后的记录...")

    # 1. 清理 price_history.csv
    if os.path.exists(HISTORY_FILE):
        rows_kept = 0
        rows_removed = 0
        header = None
        new_rows = []
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 读取表头：date,code,close
            for row in reader:
                if row and row[0] >= cutoff_date:
                    new_rows.append(row)
                    rows_kept += 1
                else:
                    rows_removed += 1
        # 写回（只有当文件有内容时才写，避免空文件丢失表头）
        if header:
            with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(new_rows)
            print(f"   ✅ price_history.csv 清理完成：保留 {rows_kept} 条，移除 {rows_removed} 条")
    else:
        print("   ⏳ price_history.csv 不存在，跳过")

    # 2. 清理 history.json
    history_file = get_output_path('history.json')
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        original_count = len(history)
        # 过滤保留最近一年的记录（history中的记录格式为 {'date': '20260623', ...}）
        new_history = [record for record in history if record.get('date', '') >= cutoff_date]
        removed_count = original_count - len(new_history)
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(new_history, f, ensure_ascii=False, indent=2)
        print(f"   ✅ history.json 清理完成：保留 {len(new_history)} 条，移除 {removed_count} 条")
    else:
        print("   ⏳ history.json 不存在，跳过")

    print("🧹 数据清理结束\n")

def get_output_path(filename):
    return os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"), filename)

def fetch_json(url, referer="https://quote.eastmoney.com/"):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            text = resp.text
            if text.startswith('jQuery') or '(' in text:
                s = text.index('(') + 1
                e = text.rindex(')')
                text = text[s:e]
            data = json.loads(text)
            return data
        except Exception as e:
            print(f"  重试 {attempt+1}: {str(e)[:50]}")
            time.sleep(1)
    return None

def get_realtime_quotes(codes):
    """用ulist接口获取实时行情（现价、涨跌幅、成交额、总市值）"""
    if not codes:
        return {}
    secids = [f"{'1.' if c.startswith('6') else '0.'}{c}" for c in codes]
    url = (
        f"http://push2.eastmoney.com/api/qt/ulist.np/get?"
        f"fltt=2&secids={','.join(secids)}&"
        f"fields=f2,f3,f6,f12,f14,f20,f21&"
        f"ut=bd1d9ddb04089700cf9c27f6f7426281"
    )
    data = fetch_json(url)
    if data and 'data' in data and data['data'].get('diff'):
        return {item['f12']: item for item in data['data']['diff']}
    return {}

# ==================== 本地历史数据管理 ====================
HISTORY_FILE = get_output_path('price_history.csv')

def update_price_history(today_str, quotes):
    """将今日收盘价更新到历史文件，确保 (date, code) 唯一"""
    rows = []
    header = ['date', 'code', 'close']
    file_exists = os.path.exists(HISTORY_FILE)
    if file_exists:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # 跳过标题
            for row in reader:
                if row:
                    rows.append(row)
    # 建立索引映射 (date, code) -> 行号
    index_map = {}
    for i, row in enumerate(rows):
        index_map[(row[0], row[1])] = i

    for code, item in quotes.items():
        close = item.get('f2', 0)
        if not close:
            continue
        key = (today_str, code)
        if key in index_map:
            rows[index_map[key]][2] = str(close)   # 更新价格
        else:
            rows.append([today_str, code, str(close)])  # 新增

    with open(HISTORY_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print("✅ 收盘价已更新至 price_history.csv（自动去重）")

def get_ma_from_local(code):
    if not os.path.exists(HISTORY_FILE):
        return None
    # 读取所有记录，按 (date, code) 分组
    records = []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['code'] == code:
                records.append((row['date'], float(row['close'])))
    if not records:
        return None

    # 按日期排序（字符串排序等同于时间顺序）
    records.sort(key=lambda x: x[0])
    # 去重：同一日期只保留最后一条（即最后写入的）
    unique = {}
    for date, close in records:
        unique[date] = close   # 覆盖，保留最后一条
    # 取最近20个交易日（注意：unique的keys是日期字符串，排序后取最后20个）
    dates = sorted(unique.keys())
    closes = [unique[d] for d in dates[-20:]]
    if len(closes) < 20:
        return None

    latest = closes[-1]
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20

    def status(price, ma):
        return "已跌破" if price < ma else "未破"
    return {
        'latest': latest,
        'ma5': round(ma5,2),
        'ma10': round(ma10,2),
        'ma20': round(ma20,2),
        'ma5_status': status(latest, ma5),
        'ma10_status': status(latest, ma10),
        'ma20_status': status(latest, ma20)
    }
# ==================== 关注列表自动提取 ====================
def load_watchlist():
    """从 history.json 中提取过去7天内出现过的板块名称"""
    history_file = get_output_path('history.json')
    watchlist = set()
    if not os.path.exists(history_file):
        return watchlist
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    for record in history:
        if record['date'] >= cutoff:
            if record.get('top_concept'):
                watchlist.add(record['top_concept'])
            if record.get('top_industry'):
                watchlist.add(record['top_industry'])
    return watchlist

# ==================== 自动构建中军池 ====================
def build_dynamic_pool(date_str):
    """自动构建今天的中军池：关注板块+涨幅前3行业+涨停前3行业+成交额前20中市值>200亿"""
    candidates = set()
    
    # 1. 从关注列表中取板块
    watchlist = load_watchlist()
    if watchlist:
        url_all = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "fid=f3&fs=m:90+t:2,m:90+t:3&pn=1&pz=10000&po=1&np=1&"
            "ut=bd1d9ddb04089700cf9c27f6f7426281&"
            "fields=f12,f14"
        )
        data_all = fetch_json(url_all)
        if data_all and 'data' in data_all and data_all['data'].get('diff'):
            for item in data_all['data']['diff']:
                if item.get('f14') in watchlist:
                    candidates.add(item['f12'])
        time.sleep(0.5)

    # 2. 从涨停家数前3的行业板块中提取
    sector_limit_file = get_output_path(f'sector_limit_up_{date_str}.txt')
    if os.path.exists(sector_limit_file):
        with open(sector_limit_file, 'r', encoding='utf-8') as f:
            top_sectors = []
            for line in f:
                if ': ' in line and '只涨停' in line:
                    top_sectors.append(line.split(':')[0].strip())
                if len(top_sectors) >= 3:
                    break
            if top_sectors:
                url2 = (
                    "https://push2.eastmoney.com/api/qt/clist/get?"
                    "fid=f3&fs=m:90+t:2&pn=1&pz=100&po=1&np=1&"
                    "ut=bd1d9ddb04089700cf9c27f6f7426281&"
                    "fields=f12,f14"
                )
                data2 = fetch_json(url2)
                if data2 and 'data' in data2 and data2['data'].get('diff'):
                    for item in data2['data']['diff']:
                        if item.get('f14') in top_sectors:
                            candidates.add(item['f12'])

    # 3. 从成交额Top20中筛选总市值>200亿的标的
    top_amount_file = get_output_path(f'top_amount_data_{date_str}.txt')
    if os.path.exists(top_amount_file):
        with open(top_amount_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '(' in line and '总市值' in line:
                    code = line.split('(')[1].split(')')[0]
                    cap_str = line.split('总市值')[1].replace('亿','').strip()
                    try:
                        market_cap = float(cap_str) if cap_str else 0
                        if market_cap >= 200:
                            candidates.add(code)
                    except:
                        pass

    # 4. 从历史中军池里补充
    history_file = get_output_path('history.json')
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        for record in history:
            if 'mid_cap_codes' in record:
                candidates.update(record['mid_cap_codes'])

    if not candidates:
        return []
    quotes = get_realtime_quotes(list(candidates))
    return list(quotes.keys())

def main():
    # 先执行数据清理（保留最近1年）
    clean_old_data()
    
    date_str = datetime.now().strftime('%Y%m%d')
    
    print("自动构建动态中军池...")
    pool = build_dynamic_pool(date_str)
    print(f"中军池: {pool}")
    
    if not pool:
        print("未找到中军标的，退出")
        return
    
    quotes = get_realtime_quotes(pool)
    
    lines = [f"日期: {date_str}", "核心中军行情 + 均线状态", ""]
    for code in pool:
        qt = quotes.get(code)
        if not qt:
            continue
        name = qt.get('f14', '')
        price = float(qt.get('f2', 0))
        pct = float(qt.get('f3', 0))
        amount = float(qt.get('f6', 0)) / 1e8
        market_cap = float(qt.get('f20', 0)) / 1e8 if qt.get('f20') else 0
        
        print(f"  处理 {name}({code}) 的均线...")
        ma = get_ma_from_local(code)
        time.sleep(0.1)
        
        if ma:
            line = (f"{name}({code}): {price:.2f} {pct:+.2f}% 成交{amount:.1f}亿 总市值{market_cap:.0f}亿 | "
                    f"5日线{ma['ma5']}({ma['ma5_status']}) "
                    f"10日线{ma['ma10']}({ma['ma10_status']}) "
                    f"20日线{ma['ma20']}({ma['ma20_status']})")
        else:
            line = f"{name}({code}): {price:.2f} {pct:+.2f}% 成交{amount:.1f}亿 (均线数据不足，需积累20天)"
        lines.append(line)
    
    fn = get_output_path(f'mid_cap_data_{date_str}.txt')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"✅ 中军数据已保存至 {fn}")
    
    update_price_history(date_str, quotes)
    
    history_file = get_output_path('history.json')
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    today_record = next((h for h in history if h['date'] == date_str), None)
    if today_record:
        today_record['mid_cap_codes'] = pool
    else:
        history.append({'date': date_str, 'mid_cap_codes': pool})
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()