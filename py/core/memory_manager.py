"""
共享记忆管理器 v2.6
- 调用 API 时传入完整 user_content (可以是元组)
- 存储记忆时只保留 memory_content（精简后的有效对话）
- 监控场景只读不写：读取共享记忆获取当日策略，但不写入任何内容
"""
import os, json, time, re
import requests as req
from datetime import datetime

MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'shared_context.json')
DEFAULT_MAX_MEMORY = 40

REPLAY_SUMMARY_PATTERNS = {
    'market_phase': r'(?:市场环境等级|market_phase)[：:]\s*[**]*([^\s，,\n]+)',
    'primary_anchor': r'(?:正式锚点|主线锚点)[：:]\s*[**]*([^\n]+)',
    'candidate': r'(?:预置锚点|候选池|挑战者)[：:]\s*[**]*([^\n]+)',
    'action': r'(?:操作要点|操作建议)[：:]\s*([^\n]+)',
    'next_plan': r'(?:明日计划|隔日策略)[：:]\s*([^\n]+)',
}

def load_memory():
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_memory(messages, max_items=DEFAULT_MAX_MEMORY):
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    if len(messages) > max_items:
        messages = messages[-max_items:]
    with open(MEMORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def compress_user_content(content):
    if len(content) > 500:
        return content[:500] + '...'
    return content

def compress_replay(reply_text):
    summary = {}
    for key, pattern in REPLAY_SUMMARY_PATTERNS.items():
        match = re.search(pattern, reply_text)
        if match:
            summary[key] = match.group(1).strip()[:100]
    if not summary:
        return reply_text[:200] + '...' if len(reply_text) > 200 else reply_text
    parts = []
    if 'market_phase' in summary: parts.append(f"市场:{summary['market_phase']}")
    if 'primary_anchor' in summary: parts.append(f"主线:{summary['primary_anchor'][:60]}")
    if 'candidate' in summary: parts.append(f"候选:{summary['candidate'][:60]}")
    if 'action' in summary: parts.append(f"操作:{summary['action'][:80]}")
    if 'next_plan' in summary: parts.append(f"计划:{summary['next_plan'][:80]}")
    return ' | '.join(parts) if parts else reply_text[:200]

def compress_monitor(reply_text):
    try:
        match = re.search(r'"summary"\s*:\s*"([^"]+)"', reply_text)
        if match: return f"[监控] {match.group(1)[:200]}"
    except: pass
    return reply_text[:200] + '...' if len(reply_text) > 200 else reply_text

def compress_chat(reply_text):
    if len(reply_text) > 200:
        return reply_text[:200] + '...'
    return reply_text

def compress_assistant_reply(reply_text, scene):
    if scene == 'replay': return compress_replay(reply_text)
    elif scene == 'monitor': return compress_monitor(reply_text)
    else: return compress_chat(reply_text)

def call_with_memory(scene, user_content, temperature=0.1, max_tokens=8192,
                     use_memory=True, max_memory_items=DEFAULT_MAX_MEMORY,
                     memory_content=None):
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        return "[错误] 未配置 DEEPSEEK_API_KEY"

    # 监控场景：只读不写（读取策略，不写入内容）
    if scene == 'monitor':
        memory = load_memory()  # 读取共享记忆，获取当日策略
        use_memory = False      # 不写入，不保存
    else:
        memory = load_memory() if use_memory else []

    # 分离 system_prompt 和 user_prompt
    system_prompt = "你是一个专业的交易分析助手。"
    actual_user_content = user_content
    if isinstance(user_content, tuple) and len(user_content) == 2:
        system_prompt = user_content[0]
        actual_user_content = user_content[1]

    messages = [{"role": "system", "content": system_prompt}]
    if memory:
        messages += memory
    messages.append({"role": "user", "content": actual_user_content})

    try:
        from prompt_builder import load_config
        try:
            cfg = load_config().get(scene, {}).get('api_params', {})
        except:
            cfg = {}
        temp = cfg.get('temperature', temperature)
        tokens = cfg.get('max_tokens', max_tokens)
        top_p_val = cfg.get('top_p', 0.9)
        freq_pen = cfg.get('frequency_penalty', 0.0)
        pres_pen = cfg.get('presence_penalty', 0.0)

        resp = req.post(
            'https://api.deepseek.com/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': messages,
                'temperature': temp,
                'max_tokens': tokens,
                'top_p': top_p_val,
                'frequency_penalty': freq_pen,
                'presence_penalty': pres_pen
            },
            timeout=300
        )
        if resp.status_code != 200:
            return f"API 调用失败: {resp.text[:200]}"

        result = resp.json()
        ai_reply = result['choices'][0]['message']['content']

        if use_memory:
            user_for_memory = memory_content if memory_content is not None else compress_user_content(actual_user_content)
            memory.append({"role": "user", "content": user_for_memory})
            memory.append({"role": "assistant", "content": compress_assistant_reply(ai_reply, scene)})
            save_memory(memory, max_memory_items)

        return ai_reply
    except Exception as e:
        print(f"[memory] 调用异常: {e}")
        return f"调用异常: {str(e)}"
