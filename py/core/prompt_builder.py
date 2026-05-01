"""
prompt_builder.py - 拼装投喂给 DeepSeek 的完整 Prompt
依赖：replay_full_*.txt, session_snapshot.json, rules_full.md, config.json (含cluster_keywords),
      market_context.txt (可选)
自动选择最新日期的数据文件。
"""
import json
import os
import glob
from datetime import datetime

def load_text(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_latest_replay(data_dir):
    """返回最新一份 replay_full_*.txt 的路径和日期字符串"""
    pattern = os.path.join(data_dir, 'replay_full_*.txt')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f'未找到任何 replay_full_*.txt 文件于 {data_dir}')
    files.sort()
    latest = files[-1]
    basename = os.path.basename(latest)
    date_str = basename.split('_')[2][:8]
    return latest, date_str

def build_system_prompt(rules_path):
    rules = load_text(rules_path)
    system = (
        "你是一个严格遵循豆包模式交易系统的首席策略分析师。\n"
        "你精通题材周期、主线识别、双锚点机制和中军/先锋的定位。\n"
        "你不依赖单一数据点，而是结合市场状态、产业背景和规则做出判断。\n\n"
        "以下是豆包模式的全部规则，你必须严格遵守：\n\n"
        f"{rules}\n\n"
        "在分析数据时，请先输出包含全景表的可读复盘报告，再输出结构化JSON。"
    )
    return system

def build_user_content(replay_path, snapshot_path, config_path, context_path=None):
    # 1. 市场数据
    data_text = load_text(replay_path)

    # 2. 快照
    snapshot = load_json(snapshot_path)
    snapshot_text = json.dumps(snapshot, ensure_ascii=False, indent=2)

    # 3. 题材关键词
    config = load_json(config_path)
    keywords = config.get('cluster_keywords', {})
    kw_text = json.dumps(keywords, ensure_ascii=False, indent=2)

    # 4. 产业背景（可选，按日期匹配）
    bg_text = ""
    if context_path and os.path.exists(context_path):
        bg_text = load_text(context_path)
        bg_text = f"\n\n【产业背景】\n{bg_text}"

    user = (
        f"## 今日市场数据\n\n{data_text}\n\n"
        f"## 题材方向关键词映射\n\n{kw_text}\n\n"
        f"## 上一交易日纵向市场快照\n\n{snapshot_text}\n"
        f"{bg_text}\n\n"
        "## 输出要求\n"
        "1. 首先输出包含全景表的完整复盘报告（Markdown格式）。\n"
        "2. 在报告末尾，输出一个完整的JSON对象，包含以下字段：\n"
        "   market_phase (decline/sideways/uptrend/retreat),\n"
        "   rhythm (数组或null),\n"
        "   primary_anchor (对象),\n"
        "   candidate_pool (数组),\n"
        "   holdings_advice,\n"
        "   next_day_plan (字符串)。\n"
        "   JSON字段应与豆包模式输出格式一致。\n"
        "3. JSON 输出前自检：rhythm 必须与 market_phase 严格对应：\n"
        "   - uptrend → [0,2,4,9,11]\n"
        "   - sideways → [0,2,4,6,8]\n"
        "   - decline → null\n"
        "   - retreat → null"
    )
    return user

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, '..', 'data')
    config_dir = os.path.join(base, '..', 'config')

    replay_path, date_str = find_latest_replay(data_dir)
    print(f'[OK] Using date: {date_str}')
    print(f'     Data source: {os.path.basename(replay_path)}')

    snapshot_path = os.path.join(config_dir, 'session_snapshot.json')
    config_path = os.path.join(config_dir, 'config.json')
    context_path = os.path.join(data_dir, f'market_context_{date_str}.txt')
    rules_path = os.path.join(base, '..', '..', 'md', 'rules_full.md')

    for f, desc in [(snapshot_path, 'session_snapshot.json'), (rules_path, 'rules_full.md'), (config_path, 'config.json')]:
        if not os.path.exists(f):
            raise FileNotFoundError(f'缺少必要文件: {desc} ({f})')

    system = build_system_prompt(rules_path)
    user = build_user_content(replay_path, snapshot_path, config_path, context_path)

    full_prompt = f"=== SYSTEM PROMPT ===\n{system}\n\n=== USER CONTENT ===\n{user}"

    feed_dir = os.path.abspath(os.path.join(base, '..', 'feeds'))
    os.makedirs(feed_dir, exist_ok=True)
    feed_path = os.path.join(feed_dir, f'feed_{date_str}.txt')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    print(f'[OK] Prompt saved to {feed_path}')

if __name__ == '__main__':
    main()