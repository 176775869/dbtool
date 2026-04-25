# coding=utf-8
"""
自动获取热门板块的均线数据 (MA5/MA10/MA20)
零配置，自动从历史数据和当日板块排名中提取板块代码，优先保障关注主线
输出：sector_ma_data_YYYYMMDD.txt
"""
import requests
import json
import time
import os
from datetime import datetime, timedelta

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

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
            return json.loads(text)
        except Exception as e:
            print(f"  重试 {attempt+1}: {str(e)[:50]}")
            time.sleep(1)
    return None

def load_watchlist():
    """
    自动生成“关注列表”：从 history.json 中提取过去7天内出现过的板块名称，
    并优先返回。
    """
    history_file = get_output_path('history.json')
    watchlist = set()
    if not os.path.exists(history_file):
        return watchlist

    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)

    # 提取过去7天的记录
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    for record in history:
        if record['date'] >= cutoff:
            # 最强概念板块
            if record.get('top_concept'):
                watchlist.add(record['top_concept'])
            # 最强行业板块 (如果有记录)
            if record.get('top_industry'):
                watchlist.add(record['top_industry'])

    return watchlist

def auto_discover_sectors(date_str):
    """
    从当日数据文件中自动发现需要计算均线的板块代码。
    优先返回关注列表中的板块，其次返回当日涨幅前 5 的概念板块。
    """
    sector_codes = []  # 最终返回的 (code, name) 列表
    watchlist = load_watchlist()
    print(f"当前关注列表: {watchlist}")

    # 1. 优先拉取“关注列表”中板块的代码
    if watchlist:
        # 批量获取所有行业/概念板块的代码
        url_all = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "fid=f3&fs=m:90+t:2,m:90+t:3&pn=1&pz=10000&po=1&np=1&"
            "ut=bd1d9ddb04089700cf9c27f6f7426281&"
            "fields=f12,f14"
        )
        data_all = fetch_json(url_all)
        if data_all and 'data' in data_all and data_all['data'].get('diff'):
            for item in data_all['data']['diff']:
                name = item.get('f14', '')
                code = item.get('f12', '')
                if name in watchlist:
                    sector_codes.append((code, name))
        time.sleep(0.5)

    # 2. 补充当日概念板块涨幅前5，避免遗漏新方向
    url_top5 = (
        "https://push2.eastmoney.com/api/qt/clist/get?"
        "fid=f3&fs=m:90+t:3&pn=1&pz=5&po=1&np=1&"
        "ut=bd1d9ddb04089700cf9c27f6f7426281&"
        "fields=f12,f14"
    )
    data_top5 = fetch_json(url_top5)
    if data_top5 and 'data' in data_top5 and data_top5['data'].get('diff'):
        for item in data_top5['data']['diff']:
            code = item.get('f12', '')
            name = item.get('f14', '')
            # 去重，只添加不重复的
            if code and not any(c[0] == code for c in sector_codes):
                sector_codes.append((code, name))

    return sector_codes

def get_sector_ma(code, name):
    """获取单个板块的均线数据"""
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        f"secid=90.{code}&fields1=f1,f2,f3,f4,f5,f6&"
        f"fields2=f51,f52,f53,f54,f55,f56,f57&"
        f"klt=101&fqt=0&end=20500101&lmt=25&ut=bd1d9ddb04089700cf9c27f6f7426281"
    )
    data = fetch_json(url)
    if not data or not data.get('data') or not data['data'].get('klines'):
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
        'ma5_status': status(latest, ma5), 'ma10_status': status(latest, ma10), 'ma20_status': status(latest, ma20)
    }

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')

    print("自动发现板块（优先关注主线）...")
    sectors = auto_discover_sectors(date_str)
    print(f"最终获取 {len(sectors)} 个板块: {[s[1] for s in sectors]}")

    if not sectors:
        print("未发现板块，退出")
        exit(1)

    lines = [f"日期: {date_str}", "板块均线状态 (优先关注主线)", ""]
    for code, name in sectors:
        print(f"  获取 {name}({code}) 的均线...")
        ma = get_sector_ma(code, name)
        time.sleep(0.5)

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
    print(f"✅ 板块均线数据已保存至 {fn}")