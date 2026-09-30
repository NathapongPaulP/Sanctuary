from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.db import Classroom, Teacher, get_async_session
from app.schema import ClassroomRead, ClassroomCreate
from uuid import uuid4, UUID

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


@router.get("", response_model=list[ClassroomRead])
async def get_classrooms(
    classroom_id: UUID | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Classroom)

    if classroom_id is not None:
        query = query.where(Classroom.id == classroom_id)

    result = await session.exec(query)
    return result.all()


@router.post("", response_model=list[ClassroomRead], status_code=201)
async def create_classrooms(
    data: list[ClassroomCreate], session: AsyncSession = Depends(get_async_session)
):
    classrooms = [
        Classroom(
            id=uuid4(),
            grade=item.grade,
            section=item.section,
            academic_year=item.academic_year,
            room=item.room,
            homeroom_teacher_id=item.homeroom_teacher_id,
        )
        for item in data
    ]

    session.add_all(classrooms)
    await session.commit()

    for c in classrooms:
        await session.refresh(c, attribute_names=["teacher"])

    return classrooms
