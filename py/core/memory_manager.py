"""
共享记忆管理器 v2.4
"""
import os, json, time, re
import requests as req
from datetime import datetime

CONTEXT_MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'shared_context.json')
CHAT_MEMORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'shared_chat.json')
DEFAULT_MAX_MEMORY = 40
CHAT_MAX_MEMORY = 30
MAX_RETRIES = 3
RETRY_DELAY = 3

def load_memory(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_memory(messages, path, max_items=DEFAULT_MAX_MEMORY):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if len(messages) > max_items:
        messages = messages[-max_items:]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def compress_content(content):
    if len(content) > 500:
        return content[:500] + '...'
    return content

def compress_replay(reply_text):
    patterns = {
        'market_phase': r'(?:市场环境等级|market_phase)[：:]\s*[**]*([^\s，,\n]+)',
        'primary_anchor': r'(?:正式锚点|主线锚点)[：:]\s*[**]*([^\n]+)',
        'candidate': r'(?:预置锚点|候选池|挑战者)[：:]\s*[**]*([^\n]+)',
        'action': r'(?:操作要点|操作建议)[：:]\s*([^\n]+)',
        'next_plan': r'(?:明日计划|隔日策略)[：:]\s*([^\n]+)',
    }
    summary = {}
    for key, pattern in patterns.items():
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
    try:
        match = re.search(r'"signals"\s*:\s*\[(.*?)\]', reply_text, re.DOTALL)
        if match:
            count = match.group(1).count('"type"') if match.group(1).strip() else 0
            return f"[监控] {count}个信号被检测到"
    except: pass
    return reply_text[:200] + '...' if len(reply_text) > 200 else reply_text

def call_with_memory(scene, user_content, temperature=0.1, max_tokens=8192,
                     use_memory=True, max_memory_items=DEFAULT_MAX_MEMORY,
                     memory_content=None, system_prompt=None):
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        return "[错误] 未配置 DEEPSEEK_API_KEY"

    if scene == 'chat':
        memory_path = CHAT_MEMORY_PATH
        max_mem = CHAT_MAX_MEMORY
        compress_user = False
        compress_ai = False
        user_for_memory = memory_content if memory_content else user_content
    else:
        memory_path = CONTEXT_MEMORY_PATH
        max_mem = max_memory_items
        compress_user = True
        compress_ai = True
        user_for_memory = memory_content if memory_content else compress_content(user_content)

    memory = load_memory(memory_path) if use_memory else []

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages += memory
    messages.append({"role": "user", "content": user_content})

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = req.post(
                'https://api.deepseek.com/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': 'deepseek-chat', 'messages': messages, 'temperature': temperature, 'max_tokens': max_tokens},
                timeout=300
            )
            if resp.status_code != 200:
                last_error = f"API 返回 {resp.status_code}: {resp.text[:200]}"
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return f"API 调用失败: {last_error}"

            result = resp.json()
            ai_reply = result['choices'][0]['message']['content']

            if use_memory:
                stored_user = user_for_memory if compress_user else user_for_memory
                memory.append({"role": "user", "content": stored_user})
                if compress_ai:
                    ai_compressed = compress_replay(ai_reply) if scene == 'replay' else compress_monitor(ai_reply)
                else:
                    ai_compressed = ai_reply
                memory.append({"role": "assistant", "content": ai_compressed})
                save_memory(memory, memory_path, max_mem)

            return ai_reply

        except req.exceptions.ConnectionError as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                print(f"[memory] 连接失败，{RETRY_DELAY}秒后重试 (第{attempt}/{MAX_RETRIES}次) ...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[memory] 重试{MAX_RETRIES}次后仍失败: {last_error}")
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"[memory] 调用异常: {last_error}")

    return f"调用失败（重试{MAX_RETRIES}次）: {last_error}"
