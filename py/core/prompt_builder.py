"""
prompt_builder.py - 读取 feed_config.json，按场景拼接投喂内容
支持进化笔记自动注入，支持策略历史加载，支持多目录搜索
System Prompt 包含角色设定、规则、数据、策略快照、系统提示、盘中时间等所有背景上下文
User Prompt 仅包含场景指令和用户自定义指令
"""
import os
import glob
import json
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'feed_config.json')
EVOLUTION_LOG_PATH = os.path.join(CONFIG_DIR, 'evolution_log.txt')
MAX_EVOLUTION_ITEMS = 15
DATA_SEARCH_DIRS = ['py/data', 'py/collectors', '.']

# 数据文件语义标签（帮助AI识别数据内容）
DATA_LABELS = {
    'index_data': '【大盘指数数据】',
    'limit_up': '【涨停个股数据】',
    'zhaban': '【炸板个股数据】',
    'limit_down': '【跌停个股数据】',
    'sector_ma': '【板块均线状态数据】',
    'sector': '【板块行情数据（含涨幅、涨跌比、主力净流入）】',
    'mid_cap': '【核心中军行情数据（含涨跌幅、成交额）】',
    'top_amount': '【全市场成交额Top20】',
    'qs_pool': '【强势股数据】',
    'market_context': '【产业催化电报】',
    'subscription': '【盘中监控数据】',
    'strategy': '【历史策略快照】',
}

def get_label(filename):
    for key, label in DATA_LABELS.items():
        if key in filename:
            return label
    return ''

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_holidays():
    cal_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'trade_calendar.json')
    if os.path.exists(cal_path):
        with open(cal_path, 'r', encoding='utf-8') as f:
            return set(json.load(f).get('holidays', []))
    return set()

def is_trade_day(dt, holidays_set):
    if dt.weekday() >= 5:
        return False
    return dt.strftime('%Y-%m-%d') not in holidays_set

def find_nearest_trade_day(dt, holidays_set, direction='next'):
    from datetime import timedelta
    delta = 1 if direction == 'next' else -1
    cur = dt + timedelta(days=delta)
    while True:
        if is_trade_day(cur, holidays_set):
            return cur
        cur = cur + timedelta(days=delta)

def get_system_note():
    today = datetime.now()
    holidays = load_holidays()
    if is_trade_day(today, holidays):
        note = f"当前日期：{today.strftime('%Y年%m月%d日')}（今日为交易日）。"
    else:
        prev_trade = find_nearest_trade_day(today, holidays, 'prev')
        next_trade = find_nearest_trade_day(today, holidays, 'next')
        note = f"当前日期：{today.strftime('%Y年%m月%d日')}（休市），上一个交易日为{prev_trade.strftime('%Y年%m月%d日')}，下一个交易日为{next_trade.strftime('%Y年%m月%d日')}。以下数据来自上一个交易日。"
    return note

def save_evolution_note(note):
    if not note or not note.strip():
        return
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"[{timestamp}] {note.strip()}\n"
    with open(EVOLUTION_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)

def load_evolution_notes():
    if not os.path.exists(EVOLUTION_LOG_PATH):
        return ""
    with open(EVOLUTION_LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    recent = lines[-MAX_EVOLUTION_ITEMS:] if len(lines) > MAX_EVOLUTION_ITEMS else lines
    if not recent:
        return ""
    return "【历史经验教训（AI 过去犯过的错，本次必须避免）】\n" + "".join(recent)

def resolve_file(file_ref, base_dir, max_limit=0, max_qs=0, max_limit_down=0, max_zhaban=0):
    if file_ref.startswith('AUTO_LATEST:'):
        pattern = file_ref[len('AUTO_LATEST:'):]
        found = []
        for d in DATA_SEARCH_DIRS:
            found.extend(glob.glob(os.path.join(base_dir, d, os.path.basename(pattern))))
        if not found:
            tried = [os.path.join(base_dir, d, os.path.basename(pattern)) for d in DATA_SEARCH_DIRS]
            raise FileNotFoundError(f"找不到匹配文件：{pattern}。搜索路径：{tried}")
        latest = sorted(found)[-1]
        print(f"[PROMPT] 加载文件: {os.path.basename(latest)}")
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()

        # 根据文件类型和配置截断
        basename = os.path.basename(latest)
        max_items = None
        if 'limit_down' in basename:
            max_items = max_limit_down if max_limit_down > 0 else None
        elif 'zhaban' in basename:
            max_items = max_zhaban if max_zhaban > 0 else None
        elif 'limit_up' in basename or 'limit' in basename:
            max_items = max_limit if max_limit > 0 else None
        elif 'qs_pool' in basename:
            max_items = max_qs if max_qs > 0 else None

        if max_items and max_items > 0:
            lines = content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('序号'):
                    header_end = i + 1
                    break
            if header_end > 0:
                content = '\n'.join(lines[:header_end + max_items])

        return content, latest
    else:
        path = os.path.join(base_dir, file_ref)
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found: {path}')
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), path

def build_prompt(scene='replay', extra_note=None):
    config = load_config()
    sc = config[scene]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # ---- 构建用户指令（纯指令，不含任何背景上下文） ----
    user_instruction = sc['prompt_intro'] + '\n\n'
    if extra_note:
        user_instruction += f"【用户额外指令（必须严格执行）】{extra_note}\n\n"
        save_evolution_note(extra_note)

    # ---- 构建 System Prompt（角色设定 + 系统提示 + 所有预加载数据） ----
    system_prompt = sc.get('system_prompt', '')
    system_prompt += '\n\n' + get_system_note()

    # 监控场景注入盘中时间
    if scene == 'monitor':
        now = datetime.now()
        time_hint = f"【盘中时间】当前时间：{now.strftime('%H:%M:%S')}（北京时间）。"
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            time_hint += " 尚未开盘，请等待9:30。"
        elif now.hour == 9 and now.minute >= 30 and now.hour < 10:
            time_hint += " 处于早盘竞价阶段，D2弱转强信号优先。"
        elif now.hour >= 10 and now.hour < 14:
            time_hint += " 处于盘中交易阶段，综合判断。"
        elif now.hour >= 14 and now.hour < 15:
            time_hint += " 处于尾盘阶段，D3中军回踩低吸信号优先。"
        else:
            time_hint += " 已经收盘，请等待下一个交易日。"
        system_prompt += '\n\n' + time_hint

    preload_parts = []

    # 进化笔记（仅复盘）
    if scene == 'replay':
        evo = load_evolution_notes()
        if evo:
            preload_parts.append(evo)
        # 历史策略快照
        history_days = sc.get('strategy_history_days', 0)
        if history_days > 0:
            strategy_pattern = os.path.join(base_dir, 'strategy_*.md')
            all_strategy_files = sorted(glob.glob(strategy_pattern), key=os.path.getmtime, reverse=True)
            for sf in all_strategy_files[:history_days]:
                with open(sf, 'r', encoding='utf-8') as f:
                    preload_parts.append(f"--- 策略快照：{os.path.basename(sf)} ---\n{f.read()}\n")

    # 所有配置文件中的文件（规则、数据等）
    for fr in sc['files']:
        try:
            content, res = resolve_file(
                fr, base_dir,
                max_limit=sc.get('max_limit_up', 0),
                max_qs=sc.get('max_qs_pool', 0),
                max_limit_down=sc.get('max_limit_down', 0),
                max_zhaban=sc.get('max_zhaban', 0)
            )
        except FileNotFoundError as e:
            if 'anchor_history' in str(e):
                continue
            raise
        label = get_label(os.path.basename(res))
        if label:
            preload_parts.append(f"{label}\n---\n{content}")
        else:
            preload_parts.append(f"--- 文件：{os.path.basename(res)} ---\n{content}")

    if preload_parts:
        system_prompt += '\n\n' + '\n\n'.join(preload_parts)

    return system_prompt, user_instruction


if __name__ == '__main__':
    sp, up = build_prompt('replay')
    print("=== SYSTEM PROMPT (first 500 chars) ===")
    print(sp[:500])
    print("\n=== USER PROMPT (first 500 chars) ===")
    print(up[:500])