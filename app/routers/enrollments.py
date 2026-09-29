from uuid import UUID, uuid4
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.db import Enrollment, get_async_session, Classroom
from app.schema import EnrollmentRead, EnrollmentCreate

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get("", response_model=list[EnrollmentRead])
async def get_students_in_classroom(
    grade: int | None = None,
    section: int | None = None,
    academic_year: int = 2569,
    session: AsyncSession = Depends(get_async_session),
):
    query = (
        select(Enrollment)
        .join(Classroom)
        .where(Classroom.academic_year == academic_year)
        .order_by(Enrollment.classroom_id, Enrollment.student_in_class_number)
    )
    if grade is not None:
        query = query.where(Classroom.grade == grade)
    if section is not None:
        query = query.where(Classroom.section == section)
    result = await session.exec(query)
    return result.all()


@router.post("", response_model=list[EnrollmentRead], status_code=201)
async def create_enrollments(
    data: list[EnrollmentCreate],
    session: AsyncSession = Depends(get_async_session),
):
    enrollments = [
        Enrollment(
            id=uuid4(),
            student_id=item.student_id,
            classroom_id=item.classroom_id,
            student_in_class_number=item.student_in_class_number,
            start_date=item.start_date,
            end_date=item.end_date,
        )
        for item in data
    ]

    session.add_all(enrollments)
    await session.commit()

    for e in enrollments:
        await session.refresh(e, attribute_names=["student"])

    return enrollments
