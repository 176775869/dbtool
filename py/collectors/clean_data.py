"""
clean_data.py - 清理 py/data 目录下的过期数据文件，保留最近3天的采集数据，
并删除临时合并/投喂/结果文件。持久文件（如日历、价格历史）不受影响。
"""
import os, glob, re
from datetime import datetime, timedelta

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
KEEP_DAYS = 3  # 保留最近几天的文件

# 不删除的持久文件（精确匹配）
KEEP_FILES = {
    'anchor_history.json', 'price_history.csv', 'shared_context.json',
    'trade_calendar.json', 'history.json', 'evolution_log.txt', 'shared_chat.json'
}

def main():
    today = datetime.now().date()
    cutoff = today - timedelta(days=KEEP_DAYS)

    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        if filename in KEEP_FILES:
            continue

        # 1. 处理带日期后缀的数据文件
        match = re.search(r'(\d{8})', filename)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, '%Y%m%d').date()
                if file_date < cutoff:
                    os.remove(filepath)
                    print(f"[CLEAN] 过期文件删除: {filename}")
            except ValueError:
                pass
            continue

        # 2. 清理临时中间文件
        if any(filename.startswith(p) for p in ['feed_', 'result_', 'replay_full_']):
            os.remove(filepath)
            print(f"[CLEAN] 临时文件删除: {filename}")

if __name__ == '__main__':
    main()