# coding=utf-8
"""获取强势股票池数据（无K线请求版）"""
import requests, json, time, os
from datetime import datetime

def get_output_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

def fetch_qs_pool_full(date_str):
    all_items = []
    page, size = 0, 200
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://quote.eastmoney.com/'
    }
    while True:
        url = (
            f"https://push2ex.eastmoney.com/getTopicQSPool?"
            f"cb=cb&ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt"
            f"&Pageindex={page}&pagesize={size}&sort=zdp%3Adesc&date={date_str}"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            text = resp.text
            s = text.index('(')+1
            e = text.rindex(')')
            data = json.loads(text[s:e])
            if data and 'data' in data:
                pool = data['data'].get('pool', [])
                if not pool:
                    break
                all_items.extend(pool)
                if len(pool) < size:
                    break
                page += 1
                time.sleep(0.5)  # 分页间隔，避免触发反爬
            else:
                break
        except Exception as e:
            print(f"  请求失败: {str(e)[:40]}")
            break
    return all_items

if __name__ == '__main__':
    date_str = datetime.now().strftime('%Y%m%d')
    print("获取强势股票池...")
    raw = fetch_qs_pool_full(date_str)
    if not raw:
        print("未获取到数据，退出")
        exit(1)

    total = len(raw)
    print(f"共获取 {total} 只强势股")

    stocks = []
    for item in raw:
        code = item.get('c', '')
        name = item.get('n', '')
        pct = float(item.get('zdp', 0))
        turnover = float(item.get('hs', 0))
        amount = float(item.get('amount', 0)) / 1e8
        lb = float(item.get('lb', 1))
        nh = int(item.get('nh', 0))

        # 趋势评分：量比*0.5 + 新高次数*0.3 + |当日涨幅|*0.2
        trend_score = lb * 0.5 + nh * 0.3 + abs(pct) * 0.2

        stocks.append({
            'name': name,
            'code': code,
            'pct': pct,
            'turnover': turnover,
            'amount': amount,
            'lb': lb,
            'nh': nh,
            'trend_score': round(trend_score, 2)
        })

    # 按趋势评分排序
    stocks.sort(key=lambda x: x['trend_score'], reverse=True)

    filename = get_output_path(f'qs_pool_data_{date_str}.txt')
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {date_str}\n")
        f.write(f"强势股总数: {len(stocks)}\n\n")
        f.write(f"{'序号':<4}{'名称':<10}{'代码':<8}{'涨幅':<8}{'换手':<8}{'成交':<10}{'量比':<8}{'新高':<6}{'趋势评分'}\n")
        f.write("-" * 75 + "\n")
        for i, s in enumerate(stocks, 1):
            f.write(f"{i:<4}{s['name']:<10}{s['code']:<8}{s['pct']:>6.1f}%{s['turnover']:>6.2f}%{s['amount']:>8.2f}亿{s['lb']:>6.1f}{s['nh']:>4}  {s['trend_score']:>6.2f}\n")

    print(f"保存完成：{filename}")