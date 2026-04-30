# coding=utf-8
"""
一键复盘入口 v3.3：AI优先，本地紧急兜底
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
from ai_engine import call_deepseek

DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
LOCK_FILE = os.path.join(DATA_DIR, 'last_strategy_date.txt')

def find_latest_replay():
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError("[ERROR] data dir not found")
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        raise FileNotFoundError("[ERROR] no replay file found")
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])

def generate_strategy_from_ai(data, ai_result):
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
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                print(f"[SKIP] today ({today}) already generated")
                return

    # 加载规则
    rules_text = ""
    rules_path = os.path.join(SCRIPT_DIR, '..', '..', 'md', 'rules_full.md')
    if os.path.exists(rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules_text = f.read()

    # ---------- AI 优先 ----------
    strategy_content = None
    anchor = load_json(GLOBAL_ANCHOR_FILE)
    ai_result = call_deepseek(data, anchor)
    
    if ai_result:
        print("[AI] DeepSeek 返回成功，使用AI结果生成策略")
        try:
            strategy_content = generate_strategy_from_ai(data, ai_result)
        except Exception as e:
            print(f"[AI] 生成策略失败: {e}，降级到本地引擎")
            ai_result = None

    # ---------- 本地紧急兜底 ----------
    if not ai_result:
        print("[LOCAL] 使用本地规则引擎")
        if not anchor or not anchor.get('primary_anchor'):
            anchor = {"primary_anchor": {}, "candidate_pool": []}
        main_lines = []
        concepts = data.get('concepts', [])
        limit_by_sector = data.get('limit_by_sector', {})
        exclude = ['昨日首板','昨夜涨停','微盘股','ST股','低价股','破净股']
        filtered = [c for c in concepts if not any(e in c['name'] for e in exclude) and c['pct'] > 2]
        sorted_concepts = sorted(filtered, key=lambda x: x['pct'], reverse=True)
        for c in sorted_concepts[:2]:
            limit_cnt = 0
            for sn, cnt in limit_by_sector.items():
                if any(kw in sn for kw in c['name'].split()):
                    limit_cnt += cnt
            main_lines.append({
                'name': c['name'],
                'score': min(5.0, 1.5 + c['pct'] * 0.3 + limit_cnt * 0.3),
                'stage': 'C',
                'capacity': c.get('amount', 0) / (data.get('sh_amount', 1) + data.get('sz_amount', 1)),
                'type': '候选',
                'roles': {'mid_cap': [], 'lianban_pioneer': None, 'trend_pioneer': None},
                'main_type': 'candidate'
            })
        phase = 'sideways'
        rhythm = [0, 2, 4, 6, 8]
        strategy_content = generate_strategy(data, anchor, main_lines,
            f"市场阶段：sideways | 节奏：[0, 2, 4, 6, 8]",
            phase, rhythm)

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