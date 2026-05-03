# coding=utf-8
"""
一键复盘入口 v7.4
"""
import os, sys, time
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from prompt_builder import build_prompt

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'data')
LOCK_FILE = os.path.join(DATA_DIR, 'last_strategy_date.txt')


def call_deepseek_with_retry(prompt_content, max_retries=2):
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        raise ValueError("未设置 DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')
    for attempt in range(max_retries + 1):
        try:
            print(f"[API] 第 {attempt + 1}/{max_retries + 1} 次尝试...")
            if attempt > 0:
                time.sleep(5 * attempt)
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt_content}],
                temperature=0.1,
                max_tokens=8192,
                timeout=300
            )
            content = response.choices[0].message.content
            if response.choices[0].finish_reason == 'length':
                print("[WARNING] 输出被截断")
            else:
                print(f"[OK] 返回成功 (attempt {attempt + 1})")
            return content
        except Exception as e:
            print(f"[ERROR] 第 {attempt + 1} 次失败: {str(e)[:200]}")
            if attempt == max_retries:
                raise
    return None


def main():
    today = datetime.now().strftime('%Y%m%d')

    # 日期锁（前端点了强制生成则跳过）
    custom_prompt = os.environ.get('CUSTOM_PROMPT', None)
    if not custom_prompt and os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                print(f"[SKIP] 今天 ({today}) 已生成策略")
                return

    print("[PROMPT] 构建复盘投喂...")
    prompt_content = build_prompt('replay', extra_note=custom_prompt)
    print(f"[PROMPT] 投喂大小: {len(prompt_content)} 字符")

    # 保存投喂内容到 data 目录
    feed_path = os.path.join(DATA_DIR, f'feed_{today}.txt')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(prompt_content)

    try:
        strategy_content = call_deepseek_with_retry(prompt_content)
    except Exception as e:
        print(f"[FATAL] API 调用最终失败: {e}")
        strategy_content = f"# 策略生成失败\n\n所有重试均失败。\n\n错误信息: {str(e)[:500]}"

    next_date = (datetime.strptime(today, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')
    out_file = os.path.join(OUTPUT_DIR, f'strategy_{next_date}.md')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(strategy_content)
    print(f"[OK] 策略已保存: {out_file}")

    # 保存结果到 data 目录
    result_path = os.path.join(DATA_DIR, f'result_{today}.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(strategy_content)

    if not custom_prompt:
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(today)
    print("[DONE] 一键复盘完成。")


if __name__ == '__main__':
    main()