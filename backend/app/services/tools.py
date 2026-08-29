from langchain_core.tools import tool

from app.db.repositories import EmployeeRepository
from app.db.session import async_session
from app.services.knowledge_base import search_handbook as retrieve_handbook


@tool
async def get_employee_info(name: str) -> str:
    """根据员工姓名查询工号、部门、职位、手机和邮箱。"""
    async with async_session() as session:
        employee = await EmployeeRepository.get_by_name(session, name)
    if not employee:
        return f"没有找到名为“{name}”的员工。"
    return (
        f"工号：{employee.employee_no}；姓名：{employee.name}；"
        f"部门编号：{employee.department_id}；职位：{employee.position}；"
        f"手机：{employee.phone}；邮箱：{employee.email}。"
    )


@tool
async def search_handbook(question: str) -> str:
    """查询公司员工手册中的考勤、休假、差旅、报销、福利和安全制度。"""
    return await retrieve_handbook(question)
