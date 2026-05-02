# coding=utf-8
"""
本地复盘服务器：静态文件 + 策略生成 + DeepSeek 对话 API
启动后访问 http://localhost:8080/tool.html
"""
import os, sys, json, glob, subprocess, logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
import requests as req# coding=utf-8
"""
本地复盘服务器 v3.0：工作台 API、聊天、策略生成
"""
import os, sys, json, glob, subprocess, logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
import requests as req

load_dotenv()

logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

HOST = '0.0.0.0'
PORT = 8080
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
WORKBOOK_DATA = None

def preload_workbook():
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
        if datetime.fromtimestamp(os.path.getmtime(cache_path)).date() == datetime.now().date():
            with open(cache_path, 'r', encoding='utf-8') as f:
                WORKBOOK_DATA = json.load(f)
            return
    WORKBOOK_DATA = load_all_workbooks(backup_dir)
    save_workbook_json(WORKBOOK_DATA, cache_path)

class ReplayHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/workbook':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(WORKBOOK_DATA if WORKBOOK_DATA else {}, ensure_ascii=False).encode('utf-8'))
            return
        super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        if self.path == '/api/chat':
            user_message = data.get('message', '').strip()
            history = data.get('history', [])
            if not user_message:
                self.send_json(400, {'error': '消息不能为空'})
                return
            if not DEEPSEEK_API_KEY:
                self.send_json(500, {'error': '未配置 DEEPSEEK_API_KEY'})
                return

            try:
                from py.core.prompt_builder import build_prompt
                base_prompt = build_prompt('chat')
            except:
                base_prompt = ""
            messages = [{'role': 'system', 'content': base_prompt}]
            for h in history[-6:]:
                messages.append(h)
            messages.append({'role': 'user', 'content': user_message})

            try:
                resp = req.post('https://api.deepseek.com/chat/completions',
                    headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                             'Content-Type': 'application/json'},
                    json={'model': 'deepseek-chat', 'messages': messages,
                          'temperature': 0.7, 'max_tokens': 2000},
                    timeout=30)
                if resp.status_code != 200:
                    self.send_json(500, {'error': f'API error: {resp.text[:200]}'})
                    return
                result = resp.json()
                reply = result['choices'][0]['message']['content']
                self.send_json(200, {'reply': reply})
            except Exception as e:
                logging.error(f"Chat error: {e}")
                self.send_json(500, {'error': str(e)})
            return

        if self.path == '/api/generate':
            force = data.get('force', False)
            custom_prompt = data.get('custom_prompt', None)  # 接收前端自定义指令
            # 如果有自定义指令，强制重新生成
            if custom_prompt:
                force = True
                
            today_str = datetime.now().strftime('%Y%m%d')
            if not force:
                strategy_files = glob.glob('strategy_*.md')
                if strategy_files:
                    latest = max(strategy_files, key=os.path.getctime)
                    with open(latest, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logging.info(f"Serving cached strategy: {latest}")
                    self.send_json(200, {'file': latest, 'content': content, 'cached': True})
                    return

            try:
                logging.info("Starting strategy generation...")
                subprocess.run(['python', 'py/collectors/merge_replay.py'],
                               cwd=os.path.dirname(os.path.abspath(__file__)),
                               capture_output=True, encoding='utf-8')
                env = os.environ.copy()
                if custom_prompt:
                    env['CUSTOM_PROMPT'] = custom_prompt
                
                result = subprocess.run(
                    ['python', 'py/core/generate_strategy.py'],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    capture_output=True,
                    encoding='utf-8',
                    env=env
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "未知错误"
                    logging.error(f"Generation failed: {error_msg}")
                    self.send_json(500, {'error': error_msg})
                    return
                strategy_files = glob.glob('strategy_*.md')
                if not strategy_files:
                    self.send_json(500, {'error': '未找到生成的策略文件'})
                    return
                latest = max(strategy_files, key=os.path.getctime)
                with open(latest, 'r', encoding='utf-8') as f:
                    content = f.read()
                logging.info(f"Strategy generated: {latest}")
                self.send_json(200, {'file': latest, 'content': content, 'cached': False})
            except Exception as e:
                logging.exception("Generation exception")
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
        pass

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not DEEPSEEK_API_KEY:
        print("⚠️ 未设置 DEEPSEEK_API_KEY")
    preload_workbook()
    print(f"Server starting on http://0.0.0.0:{PORT}/tool.html")
    HTTPServer((HOST, PORT), ReplayHandler).serve_forever()