from typing import Annotated,AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine,async_sessionmaker
from sqlmodel import SQLModel

#1，数据库地址：SQLite是一个本地文件，无需数据库软件
# sqlite+aiosqlite:/// 是异步驱动的前缀，./chat.db是文件路径
DATABASE_URL = "sqlite+aiosqlite:///./chat.db" # 数据库地址

# 2，创建异步引擎：负责连接数据库，执行SQL语句
engine = create_async_engine(DATABASE_URL, echo=True) # echo=True表示打印SQL语句，方便调试

#3，创建异步会话：负责管理数据库连接，执行增删改查操作
async_session = async_sessionmaker(engine, expire_on_commit=False,class_=AsyncSession) # expire_on_commit=False表示提交后不失效

# 4,建表：根据models.py里的table=True的类，创建对应的表
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all) # 创建表

# 5，依赖注入：在路由函数里使用Depends(get_session)就能获取一个异步会话
# 会话依赖：每个请求进来，都会创建一个新的会话，使用完毕后自动关闭
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

# 类型别名：参数写上 SessionDep,就表示“这是个数据库会话”
SessionDep = Annotated[AsyncSession, Depends(get_session)]