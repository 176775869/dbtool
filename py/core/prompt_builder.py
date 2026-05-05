import os, glob, json
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'feed_config.json')
EVOLUTION_LOG_PATH = os.path.join(CONFIG_DIR, 'evolution_log.txt')
MAX_EVOLUTION_ITEMS = 15
DATA_SEARCH_DIRS = ['py/data', 'py/collectors', '.']

DATA_LABELS = {
    'index_data': '大盘指数数据',
    'limit_up': '涨停个股数据',
    'zhaban': '炸板个股数据',
    'limit_down': '跌停个股数据',
    'sector_ma': '板块均线状态数据',
    'sector': '板块行情数据含涨幅涨跌比主力净流入',
    'mid_cap': '核心中军行情数据含涨跌幅成交额',
    'top_amount': '全市场成交额Top20',
    'qs_pool': '强势股数据',
    'market_context': '产业催化电报',
    'subscription': '盘中监控数据',
    'strategy': '历史策略快照',
}

def get_label(filename):
    for key, label in DATA_LABELS.items():
        if key in filename:
            return label
    return ''

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_system_note():
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    weekday = today.weekday()
    note = f"当前日期{date_str}"
    if weekday in [5, 6]:
        note += "今天是周末市场休市以下数据来自上一个交易日"
    elif today.month == 5 and today.day <= 5:
        note += "今天是五一假期市场休市以下数据来自节前最后一个交易日"
    else:
        note += "今天是交易日"
    return note

def save_evolution_note(note):
    if not note or not note.strip(): return
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = f"[{timestamp}] {note.strip()}\n"
    with open(EVOLUTION_LOG_PATH, 'a', encoding='utf-8') as f: f.write(entry)

def load_evolution_notes():
    if not os.path.exists(EVOLUTION_LOG_PATH): return ""
    with open(EVOLUTION_LOG_PATH, 'r', encoding='utf-8') as f: lines = f.readlines()
    recent = lines[-MAX_EVOLUTION_ITEMS:] if len(lines) > MAX_EVOLUTION_ITEMS else lines
    if not recent: return ""
    return "历史经验教训AI 过去犯过的错本次必须避免\n" + "".join(recent)

def resolve_file(file_ref, base_dir, max_limit=0, max_qs=0, max_limit_down=0, max_zhaban=0):
    if file_ref.startswith('AUTO_LATEST:'):
        pattern = file_ref[len('AUTO_LATEST:'):]
        found = []
        for d in DATA_SEARCH_DIRS:
            found.extend(glob.glob(os.path.join(base_dir, d, os.path.basename(pattern))))
        if not found:
            tried = [os.path.join(base_dir, d, os.path.basename(pattern)) for d in DATA_SEARCH_DIRS]
            raise FileNotFoundError(f"找不到匹配文件{pattern}搜索路径{tried}")
        latest = sorted(found)[-1]
        print(f"[PROMPT] 加载文件: {os.path.basename(latest)}")
        with open(latest, 'r', encoding='utf-8') as f: content = f.read()
        if 'limit_down' in os.path.basename(latest):
            max_items = max_limit_down if max_limit_down > 0 else None
        elif 'zhaban' in os.path.basename(latest):
            max_items = max_zhaban
        elif 'limit' in os.path.basename(latest) or 'limit_up' in os.path.basename(latest):
            max_items = max_limit if max_limit > 0 else None
        elif 'qs_pool' in os.path.basename(latest):
            max_items = max_qs if max_qs > 0 else None
        elif 'limit_down' in os.path.basename(latest):
            max_items = max_limit_down if max_limit_down > 0 else None
        elif 'zhaban' in os.path.basename(latest):
            max_items = max_zhaban if max_zhaban > 0 else None
        else:
            max_items = None
        if max_items is not None and max_items > 0:
            lines = content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('序号'): header_end = i + 1; break
            if header_end > 0: content = '\n'.join(lines[:header_end + max_items])
        return content, latest
    else:
        path = os.path.join(base_dir, file_ref)
        if not os.path.exists(path): raise FileNotFoundError(f'File not found: {path}')
        with open(path, 'r', encoding='utf-8') as f: return f.read(), path

def build_prompt(scene='replay', extra_note=None):
    config = load_config()
    sc = config[scene]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    prompt = sc['prompt_intro'] + '\n\n'
    prompt += f"系统提示{get_system_note()}\n\n"
    # 监控场景注入当前盘中时间
    if scene == 'monitor':
        now = datetime.now()
        time_hint = f"盘中时间当前时间{now.strftime('%H:%M:%S')}北京时间"
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            time_hint += " 尚未开盘请等待9:30"
        elif now.hour == 9 and now.minute >= 30 and now.hour < 10:
            time_hint += " 处于早盘竞价阶段D2弱转强信号优先"
        elif now.hour >= 10 and now.hour < 14:
            time_hint += " 处于盘中交易阶段综合判断"
        elif now.hour >= 14 and now.hour < 15:
            time_hint += " 处于尾盘阶段D3中军回踩低吸信号优先"
        else:
            time_hint += " 已经收盘请等待下一个交易日"
        prompt += f"{time_hint}\n\n"
    if extra_note:
        prompt += f"用户额外指令必须严格执行{extra_note}\n\n"
        save_evolution_note(extra_note)
    if scene == 'replay':
        evo = load_evolution_notes()
        if evo: prompt += f"\n{evo}\n\n"
        history_days = sc.get('strategy_history_days', 0)
        if history_days > 0:
            strategy_pattern = os.path.join(base_dir, 'strategy_*.md')
            all_strategy_files = sorted(glob.glob(strategy_pattern), key=os.path.getmtime, reverse=True)
            for sf in all_strategy_files[:history_days]:
                with open(sf, 'r', encoding='utf-8') as f:
                    content = f.read()
                prompt += f"\n--- 策略快照{os.path.basename(sf)} ---\n{content}\n"
    for fr in sc['files']:
        try:
            content, res = resolve_file(fr, base_dir, max_limit=sc.get('max_limit_up', 0), max_qs=sc.get('max_qs_pool', 0), max_limit_down=sc.get('max_limit_down', 0), max_zhaban=sc.get('max_zhaban', 0))
        except FileNotFoundError as e:
            if 'anchor_history' in str(e):
                print(f"[PROMPT] 可选文件不存在跳过: {fr}")
                continue
            raise
        label = get_label(os.path.basename(res))
        if label:
            prompt += f"\n{label}\n---\n{content}\n"
        else:
            prompt += f"\n--- 文件{os.path.basename(res)} ---\n{content}\n"
    system_prompt = sc.get('system_prompt', '你是一个专业的交易分析助手')
    return system_prompt, prompt