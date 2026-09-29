from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db import Teacher, get_async_session
from app.schema import TeacherRead, TeacherCreate
from uuid import uuid4

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("")
async def get_teachers(
    session: AsyncSession = Depends(get_async_session),
) -> list[TeacherRead]:
    results = await session.exec(select(Teacher))
    return results.all()


@router.post("", response_model=list[TeacherRead], status_code=201)
async def create_teachers(
    data: list[TeacherCreate], session: AsyncSession = Depends(get_async_session)
):
    teachers = [
        Teacher(
            id=uuid4(),
            first_name=item.first_name,
            last_name=item.last_name,
            title=item.title,
            photo=item.photo or None,
        )
        for item in data
    ]
    session.add_all(teachers)
    await session.commit()
    for t in teachers:
        await session.refresh(t)
    return teachers
