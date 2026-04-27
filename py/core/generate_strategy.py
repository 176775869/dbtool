# coding=utf-8
"""豆包模式 · 自动盘前策略生成器 v6.1 模块化版（路径修正）"""
import os
import sys
from datetime import datetime, timedelta

# 确保可以导入同目录模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config_loader import load_config
from data_parser import parse_replay
from mainline_detector import load_json, save_json, determine_main_lines, GLOBAL_ANCHOR_FILE
from strategy_writer import generate_strategy

# 数据文件目录：py/data/
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
LOCK_FILE = os.path.join(DATA_DIR, 'last_strategy_date.txt')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')  # 策略输出到项目根目录

def find_latest_replay():
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError("数据目录 py/data/ 不存在，请先运行数据采集")
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        raise FileNotFoundError("未找到复盘数据包")
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])

def main():
    replay = find_latest_replay()
    print(f"[读取] {replay}")
    data = parse_replay(replay)
    print("[解析完成]")
    today = data['date']

    # 日期锁
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            last = f.read().strip()
        if last == today:
            print(f"[跳过] 今天（{today}）的策略已生成，不再重复生成。")
            return

    anchor = load_json(GLOBAL_ANCHOR_FILE)
    if not anchor:
        anchor = {"t_day": None, "main_line": {"name": None, "stage": "E", "last_score": 0}, "history": []}
        save_json(GLOBAL_ANCHOR_FILE, anchor)

    main_lines, main_msg, mname, mstage = determine_main_lines(anchor, data)
    strategy_md = generate_strategy(data, anchor, main_lines, main_msg, mname, mstage)

    next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(strategy_md)
    print(f"[策略已保存] {out_file}")

    # 写入日期锁（记录到 data/ 目录）
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(today)
    print(strategy_md[:800])

if __name__ == '__main__':
    main()