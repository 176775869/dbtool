# coding=utf-8
"""
豆包模式复盘数据整合脚本
自动从 py 目录读取数据文件，合并为一个完整复盘数据包
"""
import os
from datetime import datetime

date_str = datetime.now().strftime('%Y%m%d')

# 关键：脚本在 py 目录里，数据文件也在同一目录
script_dir = os.path.dirname(os.path.abspath(__file__))

files = [
    (f'index_data_{date_str}.txt', '指数数据'),
    (f'limit_up_data_{date_str}.txt', '涨停板数据'),
    (f'sector_data_{date_str}.txt', '板块数据'),
]

output_file = os.path.join(script_dir, f'replay_full_{date_str}.txt')

with open(output_file, 'w', encoding='utf-8') as out:
    out.write(f"# 豆包模式复盘数据包 {date_str}\n\n")
    for fname, label in files:
        fpath = os.path.join(script_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as inf:
                content = inf.read()
            if content.strip():
                out.write(content.strip() + '\n\n')
                print(f"✅ 已合并: {fpath}（{len(content)}字符）")
            else:
                print(f"⚠️ 文件为空: {fpath}")
        except FileNotFoundError:
            print(f"⚠️ 跳过（文件不存在）: {fpath}")

print(f"\n整合完成 → {output_file}")

# 打印最终文件的前500字符，方便你确认
with open(output_file, 'r', encoding='utf-8') as check:
    preview = check.read(500)
    print(f"\n预览（前500字符）：\n{preview}")