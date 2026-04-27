# coding=utf-8
import requests
import json
import time
import os
from datetime import datetime

def get_output_path(filename):
    """获取文件保存路径：与脚本同目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, filename)

def get_index_quotes():
    url = ("http://push2.eastmoney.com/api/qt/ulist.np/get?"
           "fltt=2&secids=1.000001,0.399001,0.399006"
           "&fields=f2,f3,f4,f6,f14,f15,f16,f17,f18,f20,f21,f104,f105"
           "&ut=bd1d9ddb04089700cf9c27f6f7426281&_=" + str(int(time.time()*1000)))
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/',
    }
    while True:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'utf-8'
            if resp.content:
                data = json.loads(resp.text)
                if data.get('data') and data['data'].get('diff'):
                    return data['data']['diff']
        except Exception as e:
            print(f"获取指数失败: {e}，2秒后重试...")
            time.sleep(2)

def get_index_daily_kline(secid='1.000001', days=25):
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
           f"secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57"
           f"&klt=101&fqt=0&end=20500101&lmt={days}"
           f"&ut=bd1d9ddb04089700cf9c27f6f7426281")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.79 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/',
    }
    while True:
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'utf-8'
            data = json.loads(resp.text)
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                closes = [float(line.split(',')[2]) for line in klines]
                return closes
        except Exception as e:
            print(f"获取指数K线失败: {e}，2秒后重试...")
            time.sleep(2)

if __name__ == '__main__':
    print("正在获取指数实时行情...")
    index_list = get_index_quotes()
    if not index_list:
        print("获取失败")
        exit()
    
    index_dict = {}
    for item in index_list:
        name = item.get('f14', '')
        index_dict[name] = {
            '现价': item.get('f2', 0),
            '涨跌幅': item.get('f3', 0),
            '成交额(亿)': round(item.get('f6', 0) / 1e8, 2),
            '最高': item.get('f15', 0),
            '最低': item.get('f16', 0),
            '今开': item.get('f17', 0),
            '昨收': item.get('f18', 0),
            # 保留原始涨跌家数，用于加总
            '上涨': item.get('f104', 0) if item.get('f104') is not None else 0,
            '下跌': item.get('f105', 0) if item.get('f105') is not None else 0,
        }
    
    print("正在计算20日均线...")
    sh_closes = get_index_daily_kline('1.000001', 25)
    ma20 = round(sum(sh_closes[-20:]) / 20, 2) if len(sh_closes) >= 20 else sh_closes[-1]
    
    # 沪深两市涨跌家数相加（上证 + 深证成指）
    sh_up = index_dict.get('上证指数', {}).get('上涨', 0)
    sh_down = index_dict.get('上证指数', {}).get('下跌', 0)
    sz_up = index_dict.get('深证成指', {}).get('上涨', 0)
    sz_down = index_dict.get('深证成指', {}).get('下跌', 0)
    
    total_up = sh_up + sz_up
    total_down = sh_down + sz_down
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*40}")
    print(f"指数数据 @ {now_str}")
    for name, data in index_dict.items():
        print(f"{name}: {data['现价']:.2f}，涨跌幅 {data['涨跌幅']:+.2f}%，成交额 {data['成交额(亿)']:.2f}亿")
    print(f"上证20日均线: {ma20}")
    print(f"两市上涨家数(沪+深): {total_up}，下跌家数: {total_down}")
    print(f"{'='*40}")
    
    filename = get_output_path(f"index_data_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"日期: {datetime.now().strftime('%Y%m%d')}\n")
        for name, data in index_dict.items():
            f.write(f"{name}: {data['现价']:.2f}，涨跌幅 {data['涨跌幅']:+.2f}%，成交额 {data['成交额(亿)']:.2f}亿\n")
        f.write(f"上证20日均线: {ma20}\n")
        f.write(f"两市上涨家数: {total_up}，下跌家数: {total_down}\n")
    print(f"数据已保存到 {filename}")