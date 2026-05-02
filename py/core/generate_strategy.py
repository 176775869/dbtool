# coding=utf-8
"""
一键复盘入口 v7.3（支持前端 custom_prompt 输入）
修复了 max_tokens 截断问题
"""
import os, sys, json, re, time
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from prompt_builder import build_prompt

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', '..')
LOCK_FILE = os.path.join(OUTPUT_DIR, 'py', 'data', 'last_strategy_date.txt')
FEED_DIR = os.path.join(SCRIPT_DIR, '..', 'feeds')


def call_deepseek_with_retry(prompt_content, max_retries=2):
    api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    if not api_key:
        raise ValueError("未设置 DEEPSEEK_API_KEY")

    client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com')

    for attempt in range(max_retries + 1):
        try:
            print(f"[API] 第 {attempt + 1}/{max_retries + 1} 次尝试...")
            if attempt > 0:
                wait = 5 * attempt
                print(f"[API] 等待 {wait} 秒后重试...")
                time.sleep(wait)

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt_content}],
                temperature=0.1,
                max_tokens=8192,  # 增大到 8192，确保复盘报告完整输出
                timeout=300
            )
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            if finish_reason == 'length':
                print("[WARNING] 输出被截断，可能需要增大 max_tokens")
            else:
                print(f"[OK] 返回成功 (attempt {attempt + 1})")
            return content

        except Exception as e:
            print(f"[ERROR] 第 {attempt + 1} 次失败: {str(e)[:200]}")
            if attempt == max_retries:
                raise
    return None


def main(custom_prompt=None):
    """
    主函数。
    参数:
        custom_prompt (str, optional): 来自前端的自定义提示词，如果提供，会覆盖默认的 prompt 构建。
    """
    custom_prompt = os.environ.get('CUSTOM_PROMPT', None)
    today = datetime.now().strftime('%Y%m%d')

    # 日期锁（仅在非自定义模式下生效）
    if not custom_prompt and os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r', encoding='utf-8') as f:
            if f.read().strip() == today:
                print(f"[SKIP] 今天 ({today}) 已生成策略")
                return

    print("[PROMPT] 构建复盘投喂...")
    # 使用 custom_prompt（如果提供）作为额外的用户指令
    prompt_content = build_prompt('replay', extra_note=custom_prompt)
    print(f"[PROMPT] 投喂大小: {len(prompt_content)} 字符, 约 {len(prompt_content)//2} tokens")

    os.makedirs(FEED_DIR, exist_ok=True)
    feed_path = os.path.join(FEED_DIR, f'feed_{today}.txt')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(prompt_content)
    print(f"[FEED] 投喂内容已保存: {feed_path}")

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

    result_path = os.path.join(FEED_DIR, f'result_{today}.txt')
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write(strategy_content)

    if not custom_prompt:
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(today)
    print("[DONE] 一键复盘完成。")
    return strategy_content


if __name__ == '__main__':
    main()