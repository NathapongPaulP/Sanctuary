from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import Timetable, get_async_session
from app.schema import TimeTableCreate, TimeTableRead
from uuid import uuid4

router = APIRouter(prefix="/timetables", tags=["time_tables"])


@router.get("", response_model=list[TimeTableRead])
async def get_time_tables(session: AsyncSession = Depends(get_async_session)):
    results = await session.execute(select(Timetable))

    return results.scalars().all()


@router.post("", response_model=list[TimeTableRead], status_code=201)
async def create_time_tables(
    data: list[TimeTableCreate], session: AsyncSession = Depends(get_async_session)
):
    time_tables = [
        Timetable(
            id=uuid4(),
            day_of_the_week=item.day_of_the_week,
            start_time=item.start_time,
            end_time=item.end_time,
            room=item.room or None,
        )
        for item in data
    ]

    session.add_all(time_tables)
    await session.commit()
    for tt in time_tables:
        await session.refresh(tt)
    return time_tables
