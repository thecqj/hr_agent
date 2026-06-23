"""
数据库初始化脚本
用法: python init_db.py
"""
import asyncio
from app.database import init_db, engine


async def main():
    print("正在创建数据库表...")
    await init_db()
    print("✅ 数据库表创建完成！")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())