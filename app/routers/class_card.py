"""
{
    teacher_id:,
    techer_appropriate_data:
    {
        homeroom_class: {
            grade:,
            section:,
            academic_year:,
            current_worksheet:,
            number_of_students:,
            day:(1-5 = mon-fri with exception of if it's today return today),
            start_time:,
            worksheet_mising:,
            worksheet_waiting_to_be_grade:,
            class_subject:,
            should_pay_more_attention: (for student who are doing bad and should be checked on),
        },
        teaching_class: [
            {
                grade:,
                section:,
                academic_year:,
                current_worksheet:,
                number_of_students:,
                day:(1-5 = mon-fri with exception of if it's today return today),
                start_time:,
                worksheet_mising:,
                worksheet_waiting_to_be_grade:,
                class_subject:,
                should_pay_more_attention: (for student who are doing bad and should be checked on),
            },
                    {
                grade:,
                section:,
                academic_year:,
                current_worksheet:,
                number_of_students:,
                day:(1-5 = mon-fri with exception of if it's today return today),
                start_time:,
                worksheet_mising:,
                worksheet_waiting_to_be_grade:,
                class_subject:,
                should_pay_more_attention: (for student who are doing bad and should be checked on),
            },
                    {
                grade:,
                section:,
                academic_year:,
                current_worksheet:,
                number_of_students:,
                day:(1-5 = mon-fri with exception of if it's today return today),
                start_time:,
                worksheet_mising:,
                worksheet_waiting_to_be_grade:,
                class_subject:,
                should_pay_more_attention: (for student who are doing bad and should be checked on),
            },
            .
            .
            .
        ]
    },
}
"""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select
from app.db import (
    get_async_session,
    Classroom,
    Teacher,
    Enrollment,
    ClassSubject,
    Subject,
    Timetable,
)
from app.schema import NextSession, ClassPageData, TeacherAppropriateData, CardData
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/class_cards", tags=["class_cards"])


def minutes_since_monday(day, t):
    return (day - 1) * 24 * 60 + t.hour * 60 + t.minute


@router.get("", response_model=CardData)
async def get_class_page_data(
    teacher_id: UUID, session: AsyncSession = Depends(get_async_session)
):
    number_of_students_sq = (
        select(
            Enrollment.classroom_id,
            func.count().label("number_of_students"),
        )
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
    )

    rows = (await session.exec(stmt)).mappings().all()
    ids = [row["class_subject_id"] for row in rows]
    slots = (
        await session.exec(select(Timetable).where(Timetable.class_subject_id.in_(ids)))
    ).all()
    slots_by_cs = defaultdict(list)
    for slot in slots:
        slots_by_cs[slot.class_subject_id].append(slot)
    now = datetime.now(ZoneInfo("Asia/Bangkok"))
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

    homeroom = None
    teaching = []
    for row in rows:
        card = ClassPageData(**row, next_session=next_by_cs.get(row["class_subject_id"]))
        if row["is_homeroom"]:
            homeroom = card
        else:
            teaching.append(card)

    teacher_appropriate_data =TeacherAppropriateData(homeroom_class=homeroom, teaching_class=teaching)

    return CardData(teacher_id=teacher_id, teacher_appropriate_data=teacher_appropriate_data)
