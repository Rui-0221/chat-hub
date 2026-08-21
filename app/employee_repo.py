from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from models import Employee

class EmployeeRepository:
    """把数据库操作封装成方法，接口层只管调用"""
    @classmethod
    async def create_employee(cls ,session:AsyncSession,employee:Employee)->Employee:
        session.add(employee) # 放进会话
        await session.commit() # 提交（真写入）
        await session.refresh(employee) # 从库里读回（拿到自动生成的id)
        return employee

    @classmethod
    async def get_all_employees(cls , session: AsyncSession) -> list[Employee]:
        result = await session.execute(select(Employee))  # 查整张表
        return result.scalars().all()                     # 取所有行

    @classmethod
    async def get_employee_by_id(cls ,session:AsyncSession,employee_id:int)->Employee | None:
        result = await session.execute(select(Employee).where(Employee.id==employee_id))
        return result.scalars().first()