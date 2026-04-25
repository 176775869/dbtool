# coding=utf-8
"""
清理 py 目录下所有历史生成的临时复盘文件
保留: history.json, price_history.csv, *.py, launcher.bat, README.md 等
"""
import os
import glob
import re

script_dir = os.path.dirname(os.path.abspath(__file__))

# 匹配模式：包含 '_YYYYMMDD' 或 'YYYYMMDD' 的 txt / json 文件
patterns = [
    '*_202[0-9][0-9][0-9][0-9][0-9][0-9].txt',   # index_data_20260425.txt
    '*_202[0-9]*.json',                            # limit_up_raw_20260425.json
    'replay_full_202[0-9]*.txt',                   # replay_full_20260425_184523.txt
]

deleted_count = 0
for pattern in patterns:
    for fpath in glob.glob(os.path.join(script_dir, pattern)):
        fname = os.path.basename(fpath)
        # 跳过核心文件
        if fname in ['history.json', 'price_history.csv']:
            continue
        try:
            os.remove(fpath)
            deleted_count += 1
            print(f'已删除: {fname}')
        except Exception as e:
            print(f'删除失败 {fname}: {e}')

# 额外删除 sector_ma_data_* 和 history_compare_* 等（已被上面通配涵盖）
# 如果还有遗漏，可以在这里补充

print(f'\n清理完成，共删除 {deleted_count} 个文件。')