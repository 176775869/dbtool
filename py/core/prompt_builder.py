import os, glob, json
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'feed_config.json')
EVOLUTION_LOG_PATH = os.path.join(CONFIG_DIR, 'evolution_log.txt')
MAX_EVOLUTION_ITEMS = 15
DATA_SEARCH_DIRS = ['py/data', 'py/collectors', '.']

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_system_note():
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    weekday = today.weekday()
    note = f"当前日期：{date_str}。"
    if weekday in [5, 6]:
        note += "今天是周末，市场休市。以下数据来自上一个交易日。"
    elif today.month == 5 and today.day <= 5:
        note += "今天是五一假期，市场休市。以下数据来自节前最后一个交易日。"
    else:
        note += "今天是交易日。"
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
    return "【历史经验教训（AI 过去犯过的错，本次必须避免）】\n" + "".join(recent)

def resolve_file(file_ref, base_dir):
    if file_ref.startswith('AUTO_LATEST:'):
        pattern = file_ref[len('AUTO_LATEST:'):]
        found = []
        for d in DATA_SEARCH_DIRS:
            found.extend(glob.glob(os.path.join(base_dir, d, os.path.basename(pattern))))
        if not found:
            tried = [os.path.join(base_dir, d, os.path.basename(pattern)) for d in DATA_SEARCH_DIRS]
            raise FileNotFoundError(f"找不到匹配文件：{pattern}。搜索路径：{tried}")
        latest = sorted(found)[-1]
        with open(latest, 'r', encoding='utf-8') as f: content = f.read()
        config = load_config()
        replay_cfg = config.get('replay', {})
        if 'limit' in os.path.basename(latest):
            max_items = replay_cfg.get('max_limit_up', 30)
        elif 'qs_pool' in os.path.basename(latest):
            max_items = replay_cfg.get('max_qs_pool', 30)
        else:
            max_items = None
        if max_items is not None and max_items > 0:
            lines = content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('序号'): header_end = i + 1; break
            if header_end > 0:
                content = '\n'.join(lines[:header_end + max_items])
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
    prompt += f"【系统提示】{get_system_note()}\n\n"
    if extra_note:
        prompt += f"【用户额外指令（必须严格执行）】{extra_note}\n\n"
        save_evolution_note(extra_note)
    if scene == 'replay':
        evo = load_evolution_notes()
        if evo: prompt += f"\n{evo}\n\n"

    # --- 所有场景通用的历史策略加载 ---
    history_days = sc.get('strategy_history_days', 0)
    if history_days > 0:
        strategy_pattern = os.path.join(base_dir, 'strategy_*.md')
        all_strategy_files = sorted(glob.glob(strategy_pattern), key=os.path.getmtime, reverse=True)
        for sf in all_strategy_files[:history_days]:
            with open(sf, 'r', encoding='utf-8') as f:
                content = f.read()
            prompt += f"\n--- 策略快照：{os.path.basename(sf)} ---\n{content}\n"

    for fr in sc['files']:
        content, res = resolve_file(fr, base_dir)
        prompt += f"\n--- 文件：{os.path.basename(res)} ---\n{content}\n"
    return prompt

if __name__ == '__main__': print(build_prompt('replay')[:500])