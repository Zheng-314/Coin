"""HF Spaces 入口：切换到 backend/ 目录并以 __main__ 方式运行 server.py"""
import os
import runpy
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'backend'))
os.chdir(os.path.join(BASE, 'backend'))
os.environ.setdefault('PORT', '7860')

runpy.run_path(os.path.join(BASE, 'backend', 'server.py'), run_name='__main__')
