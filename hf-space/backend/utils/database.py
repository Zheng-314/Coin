# ==============================================================================
# 数据库连接工具
# ==============================================================================
import sqlite3
from contextlib import contextmanager
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


@contextmanager
def user_db():
    """
    用户数据库上下文管理器，自动提交/回滚和关闭连接

    用法:
        with user_db() as conn:
            conn.execute("INSERT INTO users ...")
        # 自动commit + close，异常时自动rollback + close
    """
    conn = get_user_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def item_db():
    """
    物品数据库上下文管理器，自动关闭连接

    用法:
        with item_db() as conn:
            rows = conn.execute("SELECT * FROM item").fetchall()
    """
    conn = get_item_db_connection()
    try:
        yield conn
    finally:
        conn.close()
