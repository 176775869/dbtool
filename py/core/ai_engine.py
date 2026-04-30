# coding=utf-8
"""
豆包模式 AI 引擎 v3.3 (轻量数据投喂 + 强化规则)
"""
import os, json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '你的KEY')
BASE_URL = 'https://api.deepseek.com'
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MEMORY_FILE = os.path.join(DATA_DIR, 'session_memory.json')
RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'md', 'rules_full.md')

def load_json_safe(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def build_system_prompt(anchor, data_date):
    # 1. 规则手册
    rules_text = ""
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, 'r', encoding='utf-8') as f:
            rules_text = f.read()
    
    # 2. 当前锚点状态
    primary = anchor.get('primary_anchor', {})
    challenger = anchor.get('challenger_anchor', {})
    pool = anchor.get('candidate_pool', [])
    
    anchor_summary = f"""
当前市场状态 (截止 {data_date})：
- 主锚点：{primary.get('name', '无')}，阶段 {primary.get('stage', '?')}，评分 {primary.get('last_score', 0)}
- 挑战者：{challenger.get('name', '无') if challenger else '无'}
- 候选池：{', '.join([c['name'] + '(' + c.get('stage','?') + ')' for c in pool[:3]]) if pool else '空'}
"""
    
    # 3. 历史记忆
    memory = load_json_safe(MEMORY_FILE)
    recent_summaries = ""
    if memory and 'history' in memory:
        recent = memory['history'][-3:]
        recent_summaries = "最近3日复盘摘要：\n" + "\n".join([h.get('summary', '') for h in recent])
    
    return rules_text + "\n\n" + anchor_summary + "\n\n" + recent_summaries

def call_deepseek(data, anchor):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)
    
    system_prompt = build_system_prompt(anchor, data_date=data.get('date', ''))
    # 轻量数据包：只发关键指标、概念板块涨幅、涨停板统计
    slim_data = {
        'date': data.get('date'),
        'sh_index': data.get('sh_index'),
        'sh_pct': data.get('sh_pct'),
        'sh_amount': data.get('sh_amount'),
        'sz_amount': data.get('sz_amount'),
        'total_amt': data.get('sh_amount', 0) + data.get('sz_amount', 0),
        'up_count': data.get('up_count'),
        'down_count': data.get('down_count'),
        'limit_total': data.get('limit_total'),
        'max_lianban': data.get('max_lianban'),
        'dieting_total': data.get('dieting_total'),
        'concepts': [{'name': c['name'], 'pct': c['pct'], 'amount': c['amount']} for c in data.get('concepts', [])[:10]],
        'limit_by_sector': data.get('limit_by_sector', {}),
        'top20': [{'name': m['name'], 'pct': m['pct'], 'market_cap': m['market_cap']} for m in data.get('top20', [])[:10]],
    }
    user_content = json.dumps(slim_data, ensure_ascii=False)
    
    try:
        print("[AI] 正在调用 DeepSeek V4 API ...")
        response = client.chat.completions.create(
            model="deepseek-chat",
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
        
        # 提取JSON
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif content.startswith('{'):
            content = content
        else:
            idx = content.find('{')
            if idx != -1:
                content = content[idx:]
        
        parsed = json.loads(content)
        
        # 保存记忆
        today = datetime.now().strftime('%Y%m%d')
        memory = load_json_safe(MEMORY_FILE)
        if 'history' not in memory:
            memory['history'] = []
        memory['history'].append({
            'date': today,
            'summary': parsed.get('next_day_plan', ''),
            'phase': parsed.get('market_phase', ''),
            'main_line': parsed.get('primary_anchor', {}).get('name', '')
        })
        memory['history'] = memory['history'][-30:]
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        print("[AI] DeepSeek 返回成功 (SDK v3.3)")
        return parsed
        
    except Exception as e:
        print(f"[AI ERROR] 调用失败: {str(e)[:300]}")
        return None