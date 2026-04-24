# coding=utf-8
"""清理 py 目录下的数据输出文件"""
import os
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
py_dir = os.path.join(script_dir, '..', 'py')

date_str = datetime.now().strftime('%Y%m%d')
files = [
    f'index_data_{date_str}.txt',
    f'sector_data_{date_str}.txt',
    f'limit_up_data_{date_str}.txt',
    f'replay_full_{date_str}.txt',
]

for fname in files:
    fpath = os.path.join(py_dir, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
        print(f'已删除: {fpath}')