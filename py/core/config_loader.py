# coding=utf-8
"""加载 config.json，提供全局配置"""
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'config.json')

def load_config():
    default = {
        "policy_hints": {},
        "mid_cap_map": {},
        "exclude_concepts": [],
        "current_holdings": {}
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            for k, v in default.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    else:
        print("[警告] 未找到 config.json，使用空配置")
        return default