from langchain_core.tools import tool
from db import async_session
from employee_repo import EmployeeRepository
from rag import handbook_store

# 工具一：查员工信息（调用Lesson5的repo）
@tool
async def get_employee_info(name:str)->str:
    """根据员工的姓名查询公司员工的基本信息（工号，部门，手机，邮箱）。"""
    async with async_session() as session:
        employee = await EmployeeRepository.get_employee_by_name(session,name)
        if not employee:
            return f"没有找到名为{name}的员工"
        return(
            f"工号：{employee.employee_no},姓名：{employee.name},"
            f"部门：{employee.department_id},手机：{employee.phone},邮箱：{employee.email}"
        )


# 工具二：查手册（调用Lesson6的向量库）
@tool
async def search_handbook(question:str)->str:
    """查询公司员工手册中的制度（年假，加班调休，报销，考勤等），question是用户关心的问题。"""
    docs = handbook_store.similarity_search(question,k=3)
    return "\n\n".join(doc.page_content for doc in docs)
