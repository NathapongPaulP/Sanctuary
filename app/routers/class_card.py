from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select, or_
from app.db import (
    get_async_session,
    Classroom,
    Enrollment,
    ClassSubject,
    Subject,
    Timetable,
)
from app.schema import NextSession, ClassPageData, TeacherAppropriateData, CardData
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import current_year_and_term

router = APIRouter(prefix="/class_cards", tags=["class_cards"])


def minutes_since_monday(day, t):
    return (day - 1) * 24 * 60 + t.hour * 60 + t.minute


@router.get("", response_model=CardData)
async def get_class_page_data(
    teacher_id: UUID, session: AsyncSession = Depends(get_async_session)
):

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    today = now.date()

    current_academic_year, current_term = current_year_and_term()
    
    number_of_students_sq = (
        select(
            Enrollment.classroom_id,
            func.count().label("number_of_students"),
        )
        .where(or_(Enrollment.end_date.is_(None), Enrollment.end_date >= today))
        .where(Enrollment.start_date <= today)
        .group_by(Enrollment.classroom_id)
        .subquery()
    )

    stmt = (
        select(
            ClassSubject.id.label("class_subject_id"),
            Classroom.grade,
            Classroom.section,
            Classroom.academic_year,
            func.coalesce(number_of_students_sq.c.number_of_students, 0).label(
                "number_of_students"
            ),
            Subject.name.label("subject"),
            (Classroom.homeroom_teacher_id == teacher_id).label("is_homeroom")
        )
        .select_from(ClassSubject)
        .join(Classroom, Classroom.id == ClassSubject.classroom_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .outerjoin(
            number_of_students_sq, number_of_students_sq.c.classroom_id == Classroom.id
        )
        .where(ClassSubject.teacher_id == teacher_id)
        .where(Classroom.academic_year == current_academic_year)
        .where(ClassSubject.term == current_term)
    )

    rows = (await session.exec(stmt)).mappings().all()
    ids = [row["class_subject_id"] for row in rows]
    slots = (
        await session.exec(select(Timetable).where(Timetable.class_subject_id.in_(ids)))
    ).all()
    slots_by_cs = defaultdict(list)
    for slot in slots:
        slots_by_cs[slot.class_subject_id].append(slot)
    now_min = minutes_since_monday(now.isoweekday(), now)

    def minutes_away(slot):
        return (
            minutes_since_monday(slot.day_of_the_week, slot.start_time) - now_min
        ) % (7 * 24 * 60)

    next_by_cs = {}
    for cs_id, cs_slots in slots_by_cs.items():
        nxt = min(cs_slots, key=minutes_away)
        next_by_cs[cs_id] = NextSession(
            day=nxt.day_of_the_week,
            start_time=nxt.start_time,
            is_today=nxt.day_of_the_week == now.isoweekday()
            and minutes_away(nxt) < 24 * 60,
        )

    homeroom = []
    teaching = []
    for row in rows:
        card = ClassPageData(**row, next_session=next_by_cs.get(row["class_subject_id"]))
        if row["is_homeroom"]:
            homeroom.append(card)
        else:
            teaching.append(card)

    teacher_appropriate_data =TeacherAppropriateData(homeroom_class=homeroom, teaching_class=teaching)

    return CardData(teacher_id=teacher_id, teacher_appropriate_data=teacher_appropriate_data)
