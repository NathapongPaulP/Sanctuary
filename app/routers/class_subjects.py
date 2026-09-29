from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db import ClassSubject, get_async_session
from app.schema import ClassSubjectCreate, ClassSubjectRead
from uuid import uuid4

router = APIRouter(prefix="/class_subjects", tags=["class_subjects"])


@router.get("", response_model=list[ClassSubjectRead])
async def get_class_subjects(session: AsyncSession = Depends(get_async_session)):
    results = await session.exec(select(ClassSubject))

    return results.all()


@router.post("", response_model=list[ClassSubjectRead], status_code=201)
async def create_class_subjects(
    data: list[ClassSubjectCreate], session: AsyncSession = Depends(get_async_session)
):
    class_subjects = [
        ClassSubject(
            id=uuid4(),
            classroom_id = item.classroom_id,
            subject_id=item.subject_id,
            teacher_id=item.teacher_id,
            term=item.term,
        )
        for item in data
    ]

    session.add_all(class_subjects)
    await session.commit()
    for cs in class_subjects:
        await session.refresh(cs)
    return class_subjects
