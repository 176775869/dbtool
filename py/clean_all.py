# coding=utf-8
"""
清理 py 目录下所有历史生成的临时复盘文件
保留核心配置及锚点数据
"""
import os
import glob

script_dir = os.path.dirname(os.path.abspath(__file__))

# 匹配所有带日期标记的临时文件 (txt / json)
patterns = [
    'index_data_*.txt',
    'sector_data_*.txt',
    'sector_ma_data_*.txt',
    'limit_up_data_*.txt',
    'limit_up_raw_*.json',
    'zhaban_data_*.txt',
    'limit_down_data_*.txt',
    'qs_pool_data_*.txt',
    'mid_cap_data_*.txt',
    'top_amount_data_*.txt',
    'history_compare_*.txt',
    'sector_limit_up_*.txt',
    'sector_limit_down_*.txt',
    'replay_full_*.txt',
    'last_strategy_date.txt',          # 策略生成日期锁
]

deleted = 0
for pattern in patterns:
    for fpath in glob.glob(os.path.join(script_dir, pattern)):
        fname = os.path.basename(fpath)
        # 保留核心文件
        if fname in ['history.json', 'price_history.csv', 'global_anchor.json', 'candidate_scores.json', 'config.json']:
            continue
        try:
            os.remove(fpath)
            deleted += 1
            print(f'已删除: {fname}')
        except Exception as e:
            print(f'删除失败 {fname}: {e}')

# 清理上级目录的策略文件
parent_dir = os.path.join(script_dir, '..')
strategy_pattern = os.path.join(parent_dir, 'strategy_*.md')
for fpath in glob.glob(strategy_pattern):
    fname = os.path.basename(fpath)
    try:
        os.remove(fpath)
        deleted += 1
        print(f'已删除: ../{fname}')
    except Exception as e:
        print(f'删除失败 ../{fname}: {e}')

print(f'\n清理完成，共删除 {deleted} 个文件。')