# coding=utf-8
"""
清理 py 目录下所有历史生成的临时复盘文件（含策略 .md 文件）
保留: history.json, price_history.csv, sector_anchors.json, *.py, launcher.bat 等
"""
import os
import glob

script_dir = os.path.dirname(os.path.abspath(__file__))

# 核心需要保留的文件名（不会被删除）
KEEP_FILES = {
    'history.json',
    'price_history.csv',
    'global_anchor.json',
    'clean_all.py',
    'generate_strategy.py',
    'get_history.py',
    'get_index_only.py',
    'get_limit_down.py',
    'get_limit_up.py',
    'get_mid_cap.py',
    'get_replay_lite.py',
    'get_sector.py',
    'get_sector_ma.py',
    'get_stocklist.py',
    'get_top_amount.py',
    'get_zhaban.py',
    'merge_replay.py',
    'launcher.bat',
}

# 要删除的文件模式（匹配包含 202 开头的日期标记）
delete_patterns = [
    '*_202[0-9]*.txt',
    '*_202[0-9]*.json',
    'replay_full_202[0-9]*.txt',
    'strategy_202[0-9]*.md',       # 新增：清理策略 Markdown 文件
    '*.md',                         # 安全起见，清理所有 md 文件（但会跳过保留列表）
]

deleted_count = 0
for pattern in delete_patterns:
    for fpath in glob.glob(os.path.join(script_dir, pattern)):
        fname = os.path.basename(fpath)
        # 跳过需要保留的核心文件
        if fname in KEEP_FILES:
            continue
        # 跳过脚本自身和批处理
        if fname.endswith('.py') or fname.endswith('.bat'):
            continue
        try:
            os.remove(fpath)
            deleted_count += 1
            print(f'已删除: {fname}')
        except Exception as e:
            print(f'删除失败 {fname}: {e}')

print(f'\n清理完成，共删除 {deleted_count} 个文件。')