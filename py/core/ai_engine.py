# coding=utf-8
"""
豆包模式 AI 引擎 v3.1 (修复 try-except + 适配 V4)
"""
import os, json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 自动加载 .env 中的 DEEPSEEK_API_KEY

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '你的KEY')
BASE_URL = 'https://api.deepseek.com'
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MEMORY_FILE = os.path.join(DATA_DIR, 'session_memory.json')


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
    """
    使用 OpenAI SDK 调用 DeepSeek V4 模型，返回结构化 JSON。
    """
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

    last_summary = load_last_session_summary()
    memory_context = f"【上个交易日复盘摘要】: {last_summary}\n\n" if last_summary else ""

    system_prompt = memory_context + "你是一个严格遵循豆包模式量化交易系统的策略分析引擎。根据系统规则和最新的市场数据，输出纯粹的结构化JSON，不要包含任何额外的解释。\n\n" + rules_text
    user_content = f"## 今日市场数据\n{data_pack}"

    try:
        print("[AI] 正在调用 DeepSeek V4 API ...")
        response = client.chat.completions.create(
            model="deepseek-chat",      # 先用你这个账号有权限的模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1,
            max_tokens=4000,
            stream=False
        )

        content = response.choices[0].message.content
        if not content:
            print("[AI ERROR] 模型返回内容为空")
            return None

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]

        parsed = json.loads(content)
        save_session_summary(parsed.get('next_day_plan', ''))
        print("[AI] DeepSeek V4 返回成功 (SDK)")
        return parsed

    except Exception as e:
        error_str = str(e)
        if '401' in error_str or '403' in error_str:
            print(f"[AI ERROR] 鉴权失败，请检查 API Key。")
        elif '402' in error_str:
            print(f"[AI ERROR] 账号余额不足，请充值。")
        elif '429' in error_str:
            print(f"[AI ERROR] 请求速率超限，稍后重试。")
        else:
            print(f"[AI ERROR] 调用失败: {error_str[:300]}")
        return None