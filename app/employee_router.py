from fastapi import APIRouter,HTTPException,status
from db import SessionDep
from employee_repo import EmployeeRepository
from models import Employee

employee_router = APIRouter(prefix="/employee", tags=["employee"])

# 新增员工
@employee_router.post("/add",status_code=status.HTTP_201_CREATED)
async def add_employee(employee: Employee,session:SessionDep):
    #提示：这个接口在Swagger里会显示为一个JSON表单，类型为Employee模型
    await EmployeeRepository.create_employee(session,employee)
    return{"message":"员工添加成功"}

# 查所有员工
@employee_router.get("/get_all",response_model=list[Employee])
async def get_all_employees(session:SessionDep):
    return await EmployeeRepository.get_all_employees(session)

# 根据id查员工
@employee_router.get("/get/{employee_id}",response_model=Employee)
async def get_employee(employee_id:int,session:SessionDep):
    employee = await EmployeeRepository.get_employee_by_id(session,employee_id)
    if employee:
        return employee
    else:
        raise HTTPException(status_code=404,detail="员工不存在") #404=找不到资源
    