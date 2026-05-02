"""
prompt_builder.py - 读取 feed_config.json，按场景拼接投喂内容
支持监控轻量数据、auto_collect 开关
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


def get_auto_collect():
    config = load_config()
    return config.get('auto_collect', False)


def get_system_note():
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
    if os.path.exists(CUSTOM_PROMPT_PATH):
        with open(CUSTOM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content
    return None


def build_monitor_light_data(base_dir):
    """为监控场景构建精简数据"""
    data_dir = os.path.join(base_dir, 'py', 'data')
    sections = []

    # 指数
    index_files = glob.glob(os.path.join(data_dir, 'index_only_*.txt'))
    if index_files:
        index_files.sort()
        with open(index_files[-1], 'r', encoding='utf-8') as f:
            sections.append(f.read())

    # 涨停前30
    limit_files = glob.glob(os.path.join(data_dir, 'limit_up_*.txt'))
    if limit_files:
        limit_files.sort()
        with open(limit_files[-1], 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('序号'):
                    header_end = i + 1
                    break
            trimmed = lines[:header_end] + lines[header_end:header_end+30] + ['... (仅保留前30只)']
            sections.append('\n'.join(trimmed))

    # 强势股前20
    qs_files = glob.glob(os.path.join(data_dir, 'qs_pool_*.txt'))
    if qs_files:
        qs_files.sort()
        with open(qs_files[-1], 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('序号'):
                    header_end = i + 1
                    break
            trimmed = lines[:header_end] + lines[header_end:header_end+20] + ['... (仅保留前20只)']
            sections.append('\n'.join(trimmed))

    # 板块涨幅前10
    sector_files = glob.glob(os.path.join(data_dir, 'sector_*.txt'))
    if sector_files:
        sector_files.sort()
        with open(sector_files[-1], 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            concept_start = None
            industry_start = None
            for i, line in enumerate(lines):
                if '=== 概念板块涨幅' in line:
                    concept_start = i
                if '=== 行业板块涨幅' in line:
                    industry_start = i
            if concept_start is not None:
                sections.append('\n'.join(lines[concept_start:concept_start+12]))
            if industry_start is not None:
                sections.append('\n'.join(lines[industry_start:industry_start+12]))

    # 炸板
    zhaban_files = glob.glob(os.path.join(data_dir, 'zhaban_*.txt'))
    if zhaban_files:
        zhaban_files.sort()
        with open(zhaban_files[-1], 'r', encoding='utf-8') as f:
            sections.append(f.read())

    # 成交额Top10
    top_amount_files = glob.glob(os.path.join(data_dir, 'top_amount_*.txt'))
    if top_amount_files:
        top_amount_files.sort()
        with open(top_amount_files[-1], 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            top_lines = []
            count = 0
            for line in lines:
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')):
                    top_lines.append(line)
                    count += 1
                    if count >= 10:
                        break
            if top_lines:
                sections.append('全市场成交额Top10:\n' + '\n'.join(top_lines))

    # 分时盘口订阅数据
    sub_files = glob.glob(os.path.join(data_dir, 'subscription_*.txt'))
    if sub_files:
        sub_files.sort()
        with open(sub_files[-1], 'r', encoding='utf-8') as f:
            sections.append('\n' + f.read())

    return '\n\n'.join(sections)


def resolve_file(file_ref, base_dir):
    if file_ref == '_MONITOR_LIGHT_DATA_':
        return build_monitor_light_data(base_dir), 'MONITOR_LIGHT_DATA'

    if file_ref.startswith('AUTO_LATEST:'):
        pattern = file_ref[len('AUTO_LATEST:'):]
        full_pattern = os.path.join(base_dir, pattern)
        files = glob.glob(full_pattern)
        if not files:
            raise FileNotFoundError(f'No files match {full_pattern}')
        files.sort()
        latest = files[-1]
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, latest
    else:
        path = os.path.join(base_dir, file_ref)
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found: {path}')
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), path


def build_prompt(scene='replay', extra_note=None):
    config = load_config()
    if scene not in config:
        raise ValueError(f'Unknown scene: {scene}')
    
    scene_config = config[scene]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    prompt = scene_config['prompt_intro'] + '\n\n'
    system_note = get_system_note()
    prompt += f"【系统提示】{system_note}\n\n"
    
    if extra_note:
        prompt += f"【用户额外指令（必须严格执行）】{extra_note}\n\n"
    else:
        custom_file_note = load_custom_prompt()
        if custom_file_note:
            prompt += f"【用户额外指令】{custom_file_note}\n\n"
    
    for file_ref in scene_config['files']:
        content, resolved = resolve_file(file_ref, base_dir)
        prompt += f"\n--- 文件：{os.path.basename(resolved) if resolved != 'MONITOR_LIGHT_DATA' else '盘中轻量数据'} ---\n{content}\n"
    
    return prompt


if __name__ == '__main__':
    print(build_prompt('monitor')[:500])
