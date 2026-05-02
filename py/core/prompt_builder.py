"""
prompt_builder.py - 读取 feed_config.json，按场景拼接投喂内容
支持通过 custom_prompt.txt 动态注入额外指令
"""
import os
import glob
import json
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'feed_config.json')
CUSTOM_PROMPT_PATH = os.path.join(CONFIG_DIR, 'custom_prompt.txt')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_system_note():
    """根据当前日期自动生成盘前提示（如节假日、非交易日说明）"""
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    weekday = today.weekday()
    
    note = f"当前日期：{date_str}。"
    if weekday in [5, 6]:
        note += "今天是周末，市场休市。以下数据来自上一个交易日。"
    elif today.month == 5 and today.day <= 3:
        note += "今天是五一假期，市场休市。以下数据来自节前最后一个交易日（2026年4月30日）。"
    else:
        note += "今天是交易日。"
    return note


def load_custom_prompt():
    """读取用户自定义的额外提示词（如果存在）"""
    if os.path.exists(CUSTOM_PROMPT_PATH):
        with open(CUSTOM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content
    return None


def resolve_file(file_ref, base_dir):
    """根据文件引用（支持 AUTO_LATEST 通配符）读取文件内容"""
    if file_ref.startswith('AUTO_LATEST:'):
        pattern = file_ref[len('AUTO_LATEST:'):]
        full_pattern = os.path.join(base_dir, pattern)
        files = glob.glob(full_pattern)
        if not files:
            raise FileNotFoundError(f'No files match {full_pattern}')
        files.sort()
        latest = files[-1]
        with open(latest, 'r', encoding='utf-8') as f:
            return f.read(), latest
    else:
        path = os.path.join(base_dir, file_ref)
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found: {path}')
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), path


def build_prompt(scene='replay', extra_note=None):
    """构建指定场景的完整投喂 Prompt。支持通过 extra_note 注入额外指令。"""
    config = load_config()
    if scene not in config:
        raise ValueError(f'Unknown scene: {scene}')
    
    scene_config = config[scene]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # 1. 场景基础 Prompt
    prompt = scene_config['prompt_intro'] + '\n\n'
    
    # 2. 系统自动提示（如节假日说明）
    system_note = get_system_note()
    prompt += f"【系统提示】{system_note}\n\n"
    
    # 3. 前端传入的额外指令（优先级最高）
    if extra_note:
        prompt += f"【用户额外指令（必须严格执行）】{extra_note}\n\n"
    else:
        # 如果前端没传，再尝试读取 custom_prompt.txt 文件
        custom_file_note = load_custom_prompt()
        if custom_file_note:
            prompt += f"【用户额外指令】{custom_file_note}\n\n"
    
    # 4. 拼接所有配置的文件内容
    for file_ref in scene_config['files']:
        content, resolved_path = resolve_file(file_ref, base_dir)
        prompt += f"\n--- 文件：{os.path.basename(resolved_path)} ---\n{content}\n"
    
    return prompt


if __name__ == '__main__':
    print(build_prompt('replay')[:500])