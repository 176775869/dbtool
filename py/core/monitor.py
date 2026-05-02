"""
monitor.py - 盘中实时监控引擎
"""
import os
import sys
import json
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompt_builder import build_prompt

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')


def check_signals():
    print("[MONITOR] 构建盘中监控投喂...")
    prompt_content = build_prompt('monitor')
    
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        return {"error": "未设置 DEEPSEEK_API_KEY", "signals": [], "summary": ""}

    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')
    
    try:
        print("[MONITOR] 调用 DeepSeek 检查买卖点...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个盘中监控助手。请根据提供的市场数据和昨日策略，判断当前是否有买卖点被触发。请以JSON格式输出结果，包含signals数组和summary字段。"},
                {"role": "user", "content": prompt_content}
            ],
            temperature=0.1,
            max_tokens=2048,
            timeout=120
        )
        content = response.choices[0].message.content
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return result
        else:
            return {"signals": [], "summary": content[:200], "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    except Exception as e:
        return {"error": str(e), "signals": [], "summary": "", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}


if __name__ == '__main__':
    print(json.dumps(check_signals(), ensure_ascii=False, indent=2))
