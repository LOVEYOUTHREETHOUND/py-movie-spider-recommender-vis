import pymysql
from config import Config

def init_mysql_database():
    """初始化MySQL数据库"""
    try:
        # 连接MySQL服务器
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=int(Config.MYSQL_PORT),
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD
        )
        
        with conn.cursor() as cursor:
            # 创建数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"数据库 {Config.MYSQL_DB} 创建成功")
            
        conn.close()
        print("MySQL数据库初始化完成")
        
    except Exception as e:
        print(f"MySQL数据库初始化失败: {str(e)}")
        raise

if __name__ == '__main__':
    init_mysql_database() 