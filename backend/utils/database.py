# ==============================================================================
# 数据库连接工具
# ==============================================================================
import sqlite3
from config import USER_DB_PATH, ITEM_DB_PATH

def get_user_db_connection():
    """获取用户数据库连接"""
    conn = sqlite3.connect(USER_DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def get_item_db_connection():
    """获取物品数据库连接"""
    conn = sqlite3.connect(ITEM_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
