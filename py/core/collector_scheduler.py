"""
采集调度器：根据每个文件的新鲜度判断是否需要重新采集
"""
import os
import time
import glob

DATA_DIRS = ['py/data', 'py/collectors']

SCRIPT_FILE_MAP = {
    'get_index_only.py': 'index_data_*.txt',
    'get_limit_up.py': 'limit_up_data_*.txt',
    'get_sector.py': 'sector_data_*.txt',
    'get_sector_ma.py': 'sector_ma_data_*.txt',
    'get_zhaban.py': 'zhaban_data_*.txt',
    'get_limit_down.py': 'limit_down_data_*.txt',
    'get_qs_pool.py': 'qs_pool_data_*.txt',
    'get_top_amount.py': 'top_amount_data_*.txt',
    'get_mid_cap.py': 'mid_cap_data_*.txt',
    'get_history.py': 'history_compare_*.txt',
    'get_subscription_data.py': 'subscription_*.txt',
    'market_context_builder.py': 'market_context_*.txt',
}


def get_data_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, '..', 'data')


def find_latest_file(pattern):
    data_dir = get_data_dir()
    search_pattern = os.path.join(data_dir, pattern)
    files = glob.glob(search_pattern)
    if not files:
        return None
    latest = max(files, key=os.path.getmtime)
    return os.path.getmtime(latest)


def should_collect(script_name, interval_seconds, force=False):
    if force:
        return True
    if interval_seconds <= 0:
        return True
    file_pattern = SCRIPT_FILE_MAP.get(script_name)
    if not file_pattern:
        return True
    latest_mtime = find_latest_file(file_pattern)
    if latest_mtime is None:
        return True
    elapsed = time.time() - latest_mtime
    return elapsed > interval_seconds
