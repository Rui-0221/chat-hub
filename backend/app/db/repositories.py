from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import Employee, EmployeeCreate


class EmployeeNumberConflictError(ValueError):
    """Raised when an employee number already exists."""


class EmployeeRepository:
    @staticmethod
    async def create(session: AsyncSession, payload: EmployeeCreate) -> Employee:
        employee = Employee.model_validate(payload)
        session.add(employee)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise EmployeeNumberConflictError(payload.employee_no) from exc
        await session.refresh(employee)
        return employee

    @staticmethod
    async def list(
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Employee]:
        statement = select(Employee).offset(offset).limit(limit)
        result = await session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, employee_id: int) -> Employee | None:
        return await session.get(Employee, employee_id)

    @staticmethod
    async def get_by_name(session: AsyncSession, name: str) -> Employee | None:
        statement = select(Employee).where(Employee.name == name)
        result = await session.execute(statement)
        return result.scalars().first()
