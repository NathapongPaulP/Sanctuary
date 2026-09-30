from datetime import date
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db import (
    get_async_session,
    Assignment,
    StudentAssignment,
    ClassSubject,
    Enrollment,
    AssignmentStatus,
)
from app.schema import (
    AssignmentCreate,
    AssignmentRead,
    StudentAssignmentRead,
    StudentAssignmentUpdate,
)

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentRead])
async def get_assignments(
    class_subject_id: UUID | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Assignment)
    if class_subject_id is not None:
        query = query.where(Assignment.class_subject_id == class_subject_id)
    results = await session.exec(query)
    return results.all()


@router.post("", response_model=AssignmentRead, status_code=201)
async def create_assignment(
    data: AssignmentCreate,
    session: AsyncSession = Depends(get_async_session),
):
    # ตรวจสอบว่ามีวิชานี้อยู่จริงไหม
    class_subject = await session.get(ClassSubject, data.class_subject_id)
    if not class_subject:
        raise HTTPException(status_code=404, detail="ClassSubject not found")

    # 1. สร้างชิ้นงานใหม่
    assignment = Assignment(
        id=uuid4(),
        class_subject_id=data.class_subject_id,
        title=data.title,
        description=data.description,
        max_score=data.max_score,
        due_date=data.due_date,
    )
    session.add(assignment)

    # 2. ค้นหานักเรียนทั้งหมดในห้องเรียนนี้ที่ยังศึกษาอยู่
    today = date.today()
    enrollments_query = (
        select(Enrollment.student_id)
        .where(Enrollment.classroom_id == class_subject.classroom_id)
        .where(Enrollment.start_date <= today)
        .where(or_(Enrollment.end_date.is_(None), Enrollment.end_date >= today))
    )
    students = (await session.exec(enrollments_query)).all()

    # 3. สร้างแถวสถานะ 'ค้างส่ง' ให้นักเรียนทุกคนในห้องอัตโนมัติ
    student_assignments = [
        StudentAssignment(
            id=uuid4(),
            assignment_id=assignment.id,
            student_id=student_id,
            status=AssignmentStatus.pending,
        )
        for student_id in students
    ]
    session.add_all(student_assignments)

    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.get("/{assignment_id}", response_model=AssignmentRead)
async def get_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    assignment = await session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.get("/{assignment_id}/students", response_model=list[StudentAssignmentRead])
async def get_assignment_students(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_async_session),
):
    query = select(StudentAssignment).where(StudentAssignment.assignment_id == assignment_id)
    results = await session.exec(query)
    return results.all()


# Router ย่อยสำหรับ student_assignments (เช่น อัปเดตคะแนน/สถานะการส่งงาน)
student_assignment_router = APIRouter(
    prefix="/student_assignments", tags=["student_assignments"]
)


@student_assignment_router.patch(
    "/{student_assignment_id}", response_model=StudentAssignmentRead
)
async def update_student_assignment(
    student_assignment_id: UUID,
    data: StudentAssignmentUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    item = await session.get(StudentAssignment, student_assignment_id)
    if not item:
        raise HTTPException(status_code=404, detail="StudentAssignment not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
