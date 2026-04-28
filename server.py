# coding=utf-8
"""
本地复盘服务器：静态文件 + 策略生成 API
启动后访问 http://localhost:8080/tool.html
"""
import os
import sys
import json
import subprocess
import glob
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime

HOST = '127.0.0.1'
PORT = 8080

class ReplayHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/api/generate':
            try:
                print(f"[API] 开始生成策略...")
                # 先合并数据
                subprocess.run(['python', 'py/collectors/merge_replay.py'], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True)
                # 生成策略
                result = subprocess.run(['python', 'py/core/generate_strategy.py'], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.send_json(500, {'error': result.stderr.strip()})
                    return

                # 找到最新生成的策略文件
                strategy_files = glob.glob('strategy_*.md')
                if not strategy_files:
                    self.send_json(500, {'error': '未找到生成的策略文件'})
                    return
                latest = max(strategy_files, key=os.path.getctime)
                with open(latest, 'r', encoding='utf-8') as f:
                    content = f.read()

                print(f"[API] 策略生成成功: {latest}")
                self.send_json(200, {'file': latest, 'content': content})
            except Exception as e:
                self.send_json(500, {'error': str(e)})
        else:
            self.send_error(404)

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"服务器启动: http://{HOST}:{PORT}/tool.html")
    print(f"API 地址: http://{HOST}:{PORT}/api/generate (POST)")
    HTTPServer((HOST, PORT), ReplayHandler).serve_forever()