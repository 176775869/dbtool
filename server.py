# coding=utf-8
"""
本地复盘服务器：静态文件 + 策略生成 + DeepSeek 对话 API
启动后访问 http://localhost:8080/tool.html
"""
import os, sys, json, glob, subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
import requests as req

load_dotenv()  # 加载 .env 中的 DEEPSEEK_API_KEY

HOST = '127.0.0.1'
PORT = 8080
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# 工作簿数据（保留原有逻辑）
WORKBOOK_DATA = None

def read_rules():
    """读取豆包规则文件，供 AI 对话使用"""
    rules_path = os.path.join(os.path.dirname(__file__), 'md', 'rules_full.md')
    if os.path.exists(rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            return f.read()[:6000]
    return ""

def preload_workbook():
    """加载工作簿数据（如果仍在使用该功能）"""
    global WORKBOOK_DATA
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'py'))
    try:
        from tools.workbook_loader import load_all_workbooks, save_workbook_json
    except ImportError:
        print("[工作簿] 模块未加载，跳过")
        return
    
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'py', 'data', 'workbook_cache.json')
    
    if os.path.exists(cache_path):
        cache_mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if cache_mtime.date() == datetime.now().date():
            print("[工作簿] 使用今日缓存")
            with open(cache_path, 'r', encoding='utf-8') as f:
                WORKBOOK_DATA = json.load(f)
            return
    
    print("[工作簿] 预加载所有年份数据...")
    WORKBOOK_DATA = load_all_workbooks(backup_dir)
    save_workbook_json(WORKBOOK_DATA, cache_path)


class ReplayHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # 工作簿 API（保留）
        if self.path == '/api/workbook':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            body = json.dumps(WORKBOOK_DATA if WORKBOOK_DATA else {"sheets": {}, "meta_sheets": {}}, ensure_ascii=False)
            self.wfile.write(body.encode('utf-8'))
            return
        
        return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # ==================== AI 聊天 API ====================
        if self.path == '/api/chat':
            user_message = data.get('message', '').strip()
            history = data.get('history', [])

            if not user_message:
                self.send_json(400, {'error': '消息不能为空'})
                return
            
            if not DEEPSEEK_API_KEY:
                self.send_json(500, {'error': '服务器未配置 DEEPSEEK_API_KEY'})
                return

            # 构造消息，不加任何交易规则
            messages = [{
                'role': 'system',
                'content': '你是一个友好的 AI 助手，用中文回答问题。'
            }]
            # 只保留最近 4 条历史，防止过长
            for h in history[-4:]:
                messages.append(h)
            messages.append({'role': 'user', 'content': user_message})

            try:
                resp = req.post(
                    'https://api.deepseek.com/chat/completions',
                    headers={
                        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'deepseek-chat',
                        'messages': messages,
                        'temperature': 0.7,
                        'max_tokens': 2000
                    },
                    timeout=30
                )
                if resp.status_code != 200:
                    self.send_json(500, {'error': f'DeepSeek 返回错误: {resp.text[:200]}'})
                    return
                
                result = resp.json()
                reply = result['choices'][0]['message']['content']
                self.send_json(200, {'reply': reply})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
            return

        # ==================== 策略生成/读取 API ====================
        if self.path == '/api/generate':
            force = data.get('force', False)  # 是否强制重新生成
            
            # 1. 如果不强制，先尝试返回已有的最新策略文件
            if not force:
                strategy_files = glob.glob('strategy_*.md')
                if strategy_files:
                    latest = max(strategy_files, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"[API] 返回已有策略: {latest}")
                    self.send_json(200, {'file': latest, 'content': content, 'cached': True})
                    return

            # 2. 需要生成新策略
            try:
                print("[API] 开始生成策略...")
                # 合并数据
                subprocess.run(['python', 'py/collectors/merge_replay.py'], 
                               cwd=os.path.dirname(os.path.abspath(__file__)), 
                               capture_output=True, encoding='utf-8')
                # 调用 generate_strategy.py
                result = subprocess.run(['python', 'py/core/generate_strategy.py'], 
                                        cwd=os.path.dirname(os.path.abspath(__file__)), 
                                        capture_output=True, encoding='utf-8')
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    print(f"[API] 生成失败: {error_msg}")
                    self.send_json(500, {'error': error_msg})
                    return

                # 查找最新生成的策略文件
                strategy_files = glob.glob('strategy_*.md')
                if not strategy_files:
                    self.send_json(500, {'error': '生成完成但未找到策略文件'})
                    return
                latest = max(strategy_files, key=os.path.getctime)
                with open(latest, 'r', encoding='utf-8') as f:
                    content = f.read()

                print(f"[API] 策略生成成功: {latest}")
                self.send_json(200, {'file': latest, 'content': content, 'cached': False})
            except Exception as e:
                print(f"[API] 生成异常: {str(e)}")
                self.send_json(500, {'error': str(e)})
            return

        self.send_error(404)

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        pass  # 关闭访问日志


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not DEEPSEEK_API_KEY:
        print("⚠️ 警告：未设置 DEEPSEEK_API_KEY，聊天功能不可用。请在 .env 文件中配置。")
    
    preload_workbook()
    
    print(f"\n{'='*50}")
    print(f"  服务器启动: http://{HOST}:{PORT}/tool.html")
    print(f"  聊天 API:   POST /api/chat")
    print(f"  策略 API:   POST /api/generate")
    print(f"  工作簿 API: GET  /api/workbook")
    print(f"{'='*50}\n")
    
    HTTPServer((HOST, PORT), ReplayHandler).serve_forever()