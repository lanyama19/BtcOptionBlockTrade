import asyncio
import psycopg2
from telethon import TelegramClient

# 替换为你的 API ID 和 API Hash
api_id = '11111'
api_hash = 'eeeeee'
phone = '123456'  # 你的电话号码登录用


# PostgreSQL 数据库连接参数
db_params = {
    'dbname': 'BlockTradeMsg',
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

# 创建 PostgreSQL 数据库连接
def connect_postgresql():
    try:
        conn = psycopg2.connect(**db_params)
        print("PostgreSQL connected successfully.")
        return conn
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return None

# 创建表
def create_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id BIGINT PRIMARY KEY,
                message_text TEXT,
                message_date TIMESTAMP
            );
        """)
        conn.commit()
        print("Table 'messages' ensured.")
        cursor.close()
    except Exception as e:
        print(f"Failed to create table: {e}")
        conn.rollback()

# 插入消息到 PostgreSQL
def insert_message(conn, message_id, message_text, message_date):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (message_id, message_text, message_date)
            VALUES (%s, %s, %s)
            ON CONFLICT (message_id) DO NOTHING;
        """, (message_id, message_text, message_date))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Failed to insert message {message_id}: {e}")
        conn.rollback()

# Telegram 主函数
async def fetch_telegram_messages(conn):
    # 创建 Telegram 客户端
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start(phone=phone_number)

    # 替换为目标群组的用户名或 ID
    target_group = '@laevitas'

    # 获取群组实体
    group = await client.get_entity(target_group)

    # 获取群组的所有历史消息
    async for message in client.iter_messages(group):
        # 插入消息到 PostgreSQL
        insert_message(conn, message.id, message.text, message.date)

    print("All messages fetched and stored.")

# 主入口
if __name__ == '__main__':
    # 连接 PostgreSQL
    postgres_conn = connect_postgresql()
    if postgres_conn is None:
        exit("Failed to connect to PostgreSQL, exiting.")

    # 确保表存在
    create_table(postgres_conn)

    # 运行 Telegram 客户端获取消息
    try:
        with TelegramClient('session_name', api_id, api_hash) as client:
            asyncio.run(fetch_telegram_messages(postgres_conn))
    finally:
        # 关闭 PostgreSQL 连接
        if postgres_conn:
            postgres_conn.close()
            print("PostgreSQL connection closed.")