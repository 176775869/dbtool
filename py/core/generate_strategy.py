# coding=utf-8
"""
一键复盘入口：AI优先，本地降级
"""
import os, sys, json
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config_loader import load_config
from data_parser import parse_replay
from mainline_detector import (
    load_json, save_json, determine_main_lines, GLOBAL_ANCHOR_FILE
)
from strategy_writer import generate_strategy
from ai_engine import call_deepseek  # 暂时禁用AI，等编码问题解决后再开启
#call_deepseek = None  # 强制降级到本地引擎


DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
LOCK_FILE = os.path.join(DATA_DIR, 'last_strategy_date.txt')
RULES_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'md', 'rules_full.md')

def find_latest_replay():
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError("[ERROR] data dir not found")
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        raise FileNotFoundError("[ERROR] no replay file found")
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])

def generate_strategy_from_ai(data, ai_result):
    """将AI返回的JSON转换为策略Markdown"""
    # 这里调用 strategy_writer 中的函数，把AI结果填入模板
    # 直接复用现有的 generate_strategy 函数，传入AI解析后的 main_lines
    from strategy_writer import generate_strategy as writer
    return writer(data, ai_result.get('anchor', {}), 
                  ai_result.get('main_lines', []),
                  ai_result.get('main_msg', ''),
                  ai_result.get('phase', 'unknown'),
                  ai_result.get('rhythm', []))

def main():
    replay_file = find_latest_replay()
    print(f"[READ] {replay_file}")
    data = parse_replay(replay_file)
    print("[OK] parse done")

    today = data['date']
    
    # 日期锁
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                print(f"[SKIP] today ({today}) already generated")
                return

    # 加载规则文档
    rules_text = ""
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, 'r', encoding='utf-8') as f:
            rules_text = f.read()

    # 读取 replay_full 文本
    with open(replay_file, 'r', encoding='utf-8') as f:
        data_pack = f.read()

    # ---------- AI 优先 ----------
    strategy_content = None
    ai_result = call_deepseek(data_pack, rules_text)
    
    if ai_result:
        print("[AI] DeepSeek 返回成功，使用AI结果生成策略")
        try:
            strategy_content = generate_strategy_from_ai(data, ai_result)
        except Exception as e:
            print(f"[AI] 生成策略失败: {e}，降级到本地引擎")
            ai_result = None

    # ---------- 本地降级 ----------
    if not ai_result:
        print("[LOCAL] 使用本地规则引擎")
        anchor = load_json(GLOBAL_ANCHOR_FILE)
        if not anchor:
            anchor = {"primary_anchor": {}, "candidate_pool": []}
        main_lines, main_msg, phase, rhythm = determine_main_lines(anchor, data)
        strategy_content = generate_strategy(data, anchor, main_lines, main_msg, phase, rhythm)

    # 保存策略
    next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(strategy_content or "[ERROR] 策略生成失败")
    print(f"[OK] strategy saved to {out_file}")

    # 写日期锁
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(today)

if __name__ == '__main__':
    main()