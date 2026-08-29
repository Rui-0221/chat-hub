from fastapi import APIRouter, HTTPException, Query, status

from app.db.models import EmployeeCreate, EmployeeRead
from app.db.repositories import EmployeeNumberConflictError, EmployeeRepository
from app.db.session import SessionDep


router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(payload: EmployeeCreate, session: SessionDep) -> EmployeeRead:
    try:
        return await EmployeeRepository.create(session, payload)
    except EmployeeNumberConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"员工编号 {exc.args[0]} 已存在",
        ) from exc


@router.get("", response_model=list[EmployeeRead])
async def list_employees(
    session: SessionDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
) -> list[EmployeeRead]:
    return await EmployeeRepository.list(session, offset=offset, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(employee_id: int, session: SessionDep) -> EmployeeRead:
    employee = await EmployeeRepository.get_by_id(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")
    return employee
