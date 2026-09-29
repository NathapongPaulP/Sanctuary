from fastapi import APIRouter, Depends
from app.schema import SubjectRead, SubjectCreate
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db import get_async_session, Subject
from uuid import uuid4

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectRead])
async def get_subjects(session: AsyncSession = Depends(get_async_session)):
    results = await session.exec(select(Subject))

    return results.all()


@router.post("", response_model=list[SubjectRead], status_code=201)
async def create_subjects(
    data: list[SubjectCreate], session: AsyncSession = Depends(get_async_session)
):
    subjects = [Subject(id=uuid4(), code=item.code, name=item.name) for item in data]

    session.add_all(subjects)
    await session.commit()
    for subject in subjects:
        await session.refresh(subject)
    return subjects
