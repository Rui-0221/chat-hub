from datetime import date

from sqlmodel import Field, SQLModel


class EmployeeBase(SQLModel):
    employee_no: str = Field(min_length=1, max_length=50, index=True, unique=True)
    name: str = Field(min_length=1, max_length=50, index=True)
    gender: int = Field(default=0, ge=0, le=2)
    department_id: int = Field(default=0, ge=0)
    position: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=7, max_length=20)
    email: str = Field(min_length=3, max_length=100)
    status: int = Field(default=1, ge=0, le=1)
    entry_date: date | None = None


class Employee(EmployeeBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    id: int
