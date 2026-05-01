# coding=utf-8
"""
一键复盘入口 v7.0（全自动闭环版）
流程：数据 → Prompt → API → 解析 → 更新快照 → 保存策略
"""
import os
import sys
import json
import re
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
FEED_DIR = os.path.join(SCRIPT_DIR, '..', 'feeds')
LOCK_FILE = os.path.join(DATA_DIR, 'last_strategy_date.txt')
RULES_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'md', 'rules_full.md')
SNAPSHOT_PATH = os.path.join(CONFIG_DIR, 'session_snapshot.json')

# 引入我们新写的两个核心模块
from prompt_builder import build_system_prompt, build_user_content
from session_manager import extract_json_from_response, update_snapshot


def find_latest_replay():
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"[ERROR] data dir not found: {DATA_DIR}")
    files = [f for f in os.listdir(DATA_DIR) if f.startswith('replay_full_') and f.endswith('.txt')]
    if not files:
        raise FileNotFoundError("[ERROR] no replay file found")
    files.sort(reverse=True)
    return os.path.join(DATA_DIR, files[0])


def save_feed_and_result(system_prompt, user_content, result_content, today):
    """保存投喂内容和 API 返回结果"""
    os.makedirs(FEED_DIR, exist_ok=True)

    # 保存完整 Prompt
    full_text = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n=== USER CONTENT ===\n{user_content}"
    feed_path = os.path.join(FEED_DIR, f'feed_{today}.txt')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"[FEED] 投喂内容已保存: {feed_path}")

    # 保存 API 返回
    result_path = os.path.join(FEED_DIR, f'result_{today}.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(result_content)
    print(f"[FEED] API 返回已保存: {result_path}")


def main():
    # 1. 找最新数据
    replay_file = find_latest_replay()
    print(f"[READ] {replay_file}")

    with open(replay_file, 'r', encoding='utf-8') as f:
        full_text = f.read()

    # 提取日期
    date_match = re.search(r'日期: (\d{8})', full_text)
    if date_match:
        today = date_match.group(1)
    else:
        today = datetime.now().strftime('%Y%m%d')
    print(f"[INFO] 数据日期: {today}")

    # 日期锁
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                print(f"[SKIP] 今天 ({today}) 已生成，删除锁文件可重试")
                return

    # 2. 检查必要文件
    config_path = os.path.join(CONFIG_DIR, 'config.json')
    for f, desc in [(SNAPSHOT_PATH, 'session_snapshot.json'), (RULES_PATH, 'rules_full.md'), (config_path, 'config.json')]:
        if not os.path.exists(f):
            raise FileNotFoundError(f'[ERROR] 缺少必要文件: {desc} ({f})')

    # 3. 构建 Prompt（用我们新的 prompt_builder）
    system_prompt = build_system_prompt(RULES_PATH)
    user_content = build_user_content(replay_file, SNAPSHOT_PATH, config_path)
    
    print(f"[PROMPT] 构建完成 (system: {len(system_prompt)}字符, user: {len(user_content)}字符)")

    # 4. 调用 API
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        print("[ERROR] 未设置 DEEPSEEK_API_KEY")
        return

    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')

    print("[API] 正在调用 DeepSeek ...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1,
            max_tokens=8192,  # 增大，防止 JSON 截断
            timeout=180
        )
        strategy_content = response.choices[0].message.content
        
        # 检查截断
        finish_reason = response.choices[0].finish_reason
        if finish_reason == 'length':
            print("[WARNING] API 返回被截断！需要增大 max_tokens")
        else:
            print(f"[OK] DeepSeek 返回成功 (finish_reason={finish_reason})")

    except Exception as e:
        print(f"[ERROR] API 调用失败: {e}")
        strategy_content = f"# 策略生成失败\n\n{str(e)}"
        # 即使失败也保存，方便调试
        save_feed_and_result(system_prompt, user_content, strategy_content, today)
        return

    # 5. 保存投喂和结果
    save_feed_and_result(system_prompt, user_content, strategy_content, today)

    # 6. 解析结果，更新快照
    try:
        ai_json = extract_json_from_response(strategy_content)
        import json as jmod
        snapshot = jmod.load(open(SNAPSHOT_PATH, 'r', encoding='utf-8'))
        updated = update_snapshot(snapshot, ai_json, new_date=today)
        with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
            jmod.dump(updated, f, ensure_ascii=False, indent=2)
        print(f"[SNAPSHOT] 快照已更新: today={today}, phase={updated.get('market_phase')}")
    except Exception as e:
        print(f"[WARNING] 快照更新失败（不影响策略生成）: {e}")

    # 7. 保存策略文件
    next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    out_file = os.path.join(OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(strategy_content)
    print(f"[OK] 策略已保存: {out_file}")

    # 写日期锁
    with open(LOCK_FILE, 'w', encoding='utf-8') as f:
        f.write(today)

    print("[DONE] 一键复盘完成。")


if __name__ == '__main__':
    main()