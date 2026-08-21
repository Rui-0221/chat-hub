from sqlmodel import SQLModel, Field


"""员工表：一个类 = 一张表，一个实例 = 一行数据"""
class Employee(SQLModel,table=True):
    id: int = Field(primary_key=True,index=True)  # 主键，自动增长
    employee_no: str = Field(max_length=50,unique=True)  # 员工编号，唯一索引
    name: str = Field(max_length=50,index=True)
    gender: int = Field(default=0) # 0=男，1=女
    department_id: int = Field(default=0) 
    position: str = Field(max_length=50)
    phone: str = Field(max_length=11)
    email: str = Field(max_length=100)
    status: int = Field(default=1) # 0=离职，1=在职
    entry_date: str = Field(default="") # 入职日期