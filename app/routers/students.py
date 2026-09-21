from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import Student, get_async_session
from app.schema import StudentRead, StudentCreate
from uuid import uuid4

router = APIRouter(prefix="/students", tags=["students"])


@router.get("")
async def get_students(
    session: AsyncSession = Depends(get_async_session),
) -> list[StudentRead]:
    results = await session.execute(select(Student))
    return results.scalars().all()


@router.post("", response_model=list[StudentRead], status_code=201)
async def create_students(
    data: list[StudentCreate], session: AsyncSession = Depends(get_async_session)
):
    students = [
        Student(
            id=uuid4(),
            first_name=item.first_name,
            last_name=item.last_name,
            nickname=item.nickname,
            sex=item.sex,
            birth_date=item.birth_date,
            photo=item.photo or None,
        )
        for item in data
    ]
    session.add_all(students)
    await session.commit()
    for t in students:
        await session.refresh(t)
    return students
