import sqlite3
import bcrypt

# 连接数据库
def setup_database():
    conn = sqlite3.connect('instance/user.db')
    cursor = conn.cursor()
    print("Connected to the database")
    
    # 启用外健约束
    cursor.execute("PRAGMA foreign_keys = ON")

    # 创建表
    # users表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        userRole TEXT DEFAULT 'user'
    );
    """)

    # historyRecords表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historyRecords(
        id TEXT PRIMARY KEY,
        username TEXT,
        pid TEXT,
        timestamp INTEGER,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    # favorites表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS favorites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        pid TEXT,
        timestamp INTEGER,
        FOREIGN KEY(username) REFERENCES users(username),
        UNIQUE(username, pid)
    );
    """)

    # chat_history 表（知识问答会读写该表）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        message_type TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT,
        timestamp INTEGER NOT NULL,
        FOREIGN KEY(username) REFERENCES users(username)
    );
    """)

    # 创建默认管理员账户
    cursor.execute("SELECT * FROM users WHERE username = ?",("admin",))

    if cursor.fetchone() is None:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw("admin".encode('utf-8'),salt)
        cursor.execute("INSERT INTO users (username,password,userRole) VALUES(?,?,?)",
        ("admin",hashed_password.decode('utf-8'),"admin"))
        print("Admin user created.")
    
    conn.commit()
    conn.close()

if __name__=='__main__':
    setup_database()
    print("Database setup complete.")