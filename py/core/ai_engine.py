# coding=utf-8
"""
豆包模式 AI 引擎 v2.3（终极修复：绕过所有编码 + 日志记录）
"""
import os
import json
import http.client
from datetime import datetime

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '你的KEY')
DEEPSEEK_HOST = 'api.deepseek.com'
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MEMORY_FILE = os.path.join(DATA_DIR, 'session_memory.json')

# 全局缓存，避免重复加载
_reason_cache = {}  # {date_str: {code: reason}}


def load_last_session_summary():
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            memory = json.load(f)
            return memory.get('summary', '')
    except:
        return ''


def save_session_summary(ai_content):
    os.makedirs(DATA_DIR, exist_ok=True)
    summary = {
        'date': datetime.now().strftime('%Y%m%d'),
        'summary': ai_content[:800]
    }
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def call_deepseek(data_pack, rules_text):
    global _reason_cache
    
    last_summary = load_last_session_summary()
    memory_context = f"【上个交易日复盘摘要】: {last_summary}\n\n" if last_summary else ""

    system_prompt = memory_context + "你是一个严格遵循豆包模式量化交易系统的策略分析引擎。根据系统规则和最新的市场数据，输出纯粹的结构化JSON，不要包含任何额外的解释。\n\n" + rules_text

    payload = {
        "model": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 4000,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"## 今日市场数据\n{data_pack}"}
        ]
    }

    try:
        # 用 http.client 直接发请求，完全控制编码
        body = json.dumps(payload, ensure_ascii=False)
        conn = http.client.HTTPSConnection(DEEPSEEK_HOST, timeout=120)
        conn.request(
            'POST',
            '/v1/chat/completions',
            body=body.encode('utf-8'),
            headers={
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            }
        )
        resp = conn.getresponse()
        
        # 关键修复：先取原始字节，再显式用utf-8解码
        raw_data = resp.read()
        resp_body = raw_data.decode('utf-8', errors='ignore')
        conn.close()

        if resp.status != 200:
            print(f'[AI ERROR] HTTP {resp.status}: {resp_body[:200]}')
            # 保存错误日志
            with open(os.path.join(DATA_DIR, 'ai_error.log'), 'w', encoding='utf-8') as f:
                f.write(resp_body)
            return None

        result = json.loads(resp_body)
        content = result['choices'][0]['message']['content']

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]

        parsed = json.loads(content)
        save_session_summary(parsed.get('next_day_plan', ''))
        
        print('[AI] DeepSeek 返回成功（v2.3修复版）')
        return parsed

    except json.JSONDecodeError as e:
        print(f'[AI ERROR] JSON解析失败: {e}')
        print(f'[AI DEBUG] 响应内容前300字符: {content[:300] if "content" in dir() else "无"}')
        return None
    except http.client.HTTPException as e:
        print(f'[AI ERROR] HTTP连接异常: {e}')
        return None
    except Exception as e:
        print(f'[AI ERROR] 未知错误: {type(e).__name__}: {e}')
        return None