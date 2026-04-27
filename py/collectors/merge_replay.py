# coding=utf-8
"""
豆包模式复盘数据整合脚本
自动发现所有数据文件并合并为一个完整复盘数据包，输出到 py/data/
"""
import os
from datetime import datetime

now = datetime.now()
date_str = now.strftime('%Y%m%d')
time_str = now.strftime('%H%M%S')

script_dir = os.path.dirname(os.path.abspath(__file__))
# 输出到上一级的 data 目录
output_dir = os.path.join(script_dir, '..', 'data')
os.makedirs(output_dir, exist_ok=True)

files = [
    (f'index_data_{date_str}.txt', '指数数据'),
    (f'limit_up_data_{date_str}.txt', '涨停板数据'),
    (f'zhaban_data_{date_str}.txt', '炸板数据'),
    (f'limit_down_data_{date_str}.txt', '跌停板数据'),
    (f'qs_pool_data_{date_str}.txt', '强势股池'),
    (f'sector_data_{date_str}.txt', '板块数据'),
    (f'sector_ma_data_{date_str}.txt', '板块均线'),
    (f'sector_limit_up_{date_str}.txt', '板块涨停统计'),
    (f'sector_limit_down_{date_str}.txt', '板块跌停统计'),
    (f'mid_cap_data_{date_str}.txt', '核心中军行情'),
    (f'top_amount_data_{date_str}.txt', '成交额Top20'),
    (f'history_compare_{date_str}.txt', '历史数据对比'),
]

output_file = os.path.join(output_dir, f'replay_full_{date_str}_{time_str}.txt')

with open(output_file, 'w', encoding='utf-8') as out:
    out.write(f"# 豆包模式复盘数据包 {date_str} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}\n\n")
    for fname, label in files:
        fpath = os.path.join(script_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as inf:
                content = inf.read()
            if content.strip():
                out.write(content.strip() + '\n\n')
                print(f"✅ 已合并: {fname} ({len(content)}字符)")
            else:
                print(f"⚠️ 文件为空: {fname}")
        except FileNotFoundError:
            print(f"⚠️ 跳过（文件不存在）: {fname}")

print(f"\n整合完成 → {output_file}")

with open(output_file, 'r', encoding='utf-8') as check:
    preview = check.read(500)
    print(f"\n预览（前500字符）：\n{preview}")