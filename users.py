import sqlite3

database_PATH = 'user_data.db'

# 创建用户表并插入初始数据
def create_users_table():
    conn = sqlite3.connect(database_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    # insert user login data
    users = [
        ('warwick001', '12345678'),
        ('warwick002', 'qwertyui')
    ]

    cursor.executemany('INSERT OR IGNORE INTO Users (user_id, password) VALUES (?, ?)', users)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_users_table()
    print("User database created and initial users inserted.")