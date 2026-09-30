import enum
import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import Field, Relationship, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

# ---------- Enums ----------


class Sex(str, enum.Enum):
    M = "M"
    F = "F"


class Status(str, enum.Enum):
    present = "มา"
    absent = "ขาด"
    late = "สาย"
    sick_leave = "ลาป่วย"
    personal_leave = "ลากิจ"


class AssignmentStatus(str, enum.Enum):
    pending = "ค้างส่ง"
    submitted = "ส่งแล้ว"
    graded = "ตรวจแล้ว"


# ---------- People ----------


class Teacher(SQLModel, table=True):
    __tablename__ = "teacher"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    first_name: str
    last_name: str
    photo: str | None = None

    homeroom_classrooms: list["Classroom"] = Relationship(back_populates="teacher")
    class_subjects: list["ClassSubject"] = Relationship(back_populates="teacher")
    attendance_sessions: list["AttendanceSession"] = Relationship(
        back_populates="teacher"
    )
    follow_up_notes: list["FollowUpNote"] = Relationship(back_populates="teacher")


class Student(SQLModel, table=True):
    __tablename__ = "student"

    id: str = Field(primary_key=True, max_length=10)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    nickname: str = Field(max_length=15)
    sex: Sex = Field(sa_type=Enum(Sex, name="sex"))
    birth_date: date
    photo: str | None = None

    enrollments: list["Enrollment"] = Relationship(back_populates="student")
    guardian_links: list["StudentGuardian"] = Relationship(back_populates="student")
    attendances: list["Attendance"] = Relationship(back_populates="student")
    follow_up_notes: list["FollowUpNote"] = Relationship(back_populates="student")
    student_assignments: list["StudentAssignment"] = Relationship(
        back_populates="student"
    )


class Guardian(SQLModel, table=True):
    __tablename__ = "guardian"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=30)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    phone: str | None = Field(default=None, max_length=15)

    student_links: list["StudentGuardian"] = Relationship(back_populates="guardian")


class StudentGuardian(SQLModel, table=True):
    __tablename__ = "student_guardian"

    student_id: str = Field(
        foreign_key="student.id", ondelete="CASCADE", primary_key=True, max_length=10
    )
    guardian_id: uuid.UUID = Field(
        foreign_key="guardian.id", ondelete="CASCADE", primary_key=True
    )
    relation: str
    is_primary: bool

    student: Student = Relationship(back_populates="guardian_links")
    guardian: Guardian = Relationship(back_populates="student_links")


# ---------- School structure ----------


class Subject(SQLModel, table=True):
    __tablename__ = "subject"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(max_length=10, unique=True)
    name: str = Field(max_length=50)

    class_subjects: list["ClassSubject"] = Relationship(back_populates="subject")


class Classroom(SQLModel, table=True):
    __tablename__ = "classroom"
    __table_args__ = (UniqueConstraint("grade", "section", "academic_year"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    homeroom_teacher_id: uuid.UUID = Field(
        foreign_key="teacher.id", ondelete="RESTRICT"
    )
    grade: int
    section: int
    academic_year: int
    room: str | None = Field(default=None, max_length=10)

    teacher: Teacher = Relationship(back_populates="homeroom_classrooms")
    enrollments: list["Enrollment"] = Relationship(back_populates="classroom")
    class_subjects: list["ClassSubject"] = Relationship(back_populates="classroom")


class Enrollment(SQLModel, table=True):
    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("student_id", "classroom_id"),
        UniqueConstraint("classroom_id", "student_in_class_number"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: str = Field(foreign_key="student.id", ondelete="CASCADE", max_length=10)
    classroom_id: uuid.UUID = Field(foreign_key="classroom.id", ondelete="CASCADE")
    student_in_class_number: int
    start_date: date
    end_date: date | None = None

    student: Student = Relationship(back_populates="enrollments")
    classroom: Classroom = Relationship(back_populates="enrollments")


class ClassSubject(SQLModel, table=True):
    __tablename__ = "class_subject"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    classroom_id: uuid.UUID = Field(foreign_key="classroom.id", ondelete="CASCADE")
    subject_id: uuid.UUID = Field(foreign_key="subject.id", ondelete="CASCADE")
    teacher_id: uuid.UUID = Field(foreign_key="teacher.id", ondelete="RESTRICT")
    term: int

    classroom: Classroom = Relationship(back_populates="class_subjects")
    subject: Subject = Relationship(back_populates="class_subjects")
    teacher: Teacher = Relationship(back_populates="class_subjects")
    timetables: list["Timetable"] = Relationship(back_populates="class_subject")
    assignments: list["Assignment"] = Relationship(back_populates="class_subject")


class Timetable(SQLModel, table=True):
    __tablename__ = "timetable"
    __table_args__ = (
        CheckConstraint("day_of_the_week BETWEEN 1 AND 5"),  # 1=Mon ... 5=Fri
        CheckConstraint("end_time > start_time"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    class_subject_id: uuid.UUID = Field(
        foreign_key="class_subject.id", ondelete="CASCADE"
    )
    day_of_the_week: int
    start_time: time
    end_time: time
    room: str | None = Field(default=None, max_length=10)

    class_subject: ClassSubject = Relationship(back_populates="timetables")
    attendance_sessions: list["AttendanceSession"] = Relationship(
        back_populates="timetable"
    )


# ---------- Attendance ----------


class AttendanceSession(SQLModel, table=True):
    __tablename__ = "attendance_session"
    __table_args__ = (UniqueConstraint("timetable_id", "date"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    timetable_id: uuid.UUID = Field(foreign_key="timetable.id", ondelete="CASCADE")
    teacher_id: uuid.UUID = Field(foreign_key="teacher.id", ondelete="RESTRICT")
    date: date
    recorded_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )

    timetable: Timetable = Relationship(back_populates="attendance_sessions")
    teacher: Teacher = Relationship(back_populates="attendance_sessions")
    attendances: list["Attendance"] = Relationship(back_populates="session")


class Attendance(SQLModel, table=True):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        foreign_key="attendance_session.id", ondelete="CASCADE"
    )
    student_id: str = Field(foreign_key="student.id", ondelete="CASCADE", max_length=10)
    status: Status = Field(
        sa_type=Enum(
            Status, name="status", values_callable=lambda e: [m.value for m in e]
        )
    )
    note: str | None = None
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )

    session: AttendanceSession = Relationship(back_populates="attendances")
    student: Student = Relationship(back_populates="attendances")


# ---------- Follow-up ----------


class FollowUpNote(SQLModel, table=True):
    __tablename__ = "follow_up_note"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: str = Field(foreign_key="student.id", ondelete="CASCADE", max_length=10)
    teacher_id: uuid.UUID = Field(foreign_key="teacher.id", ondelete="RESTRICT")
    action_date: date
    note: str
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )

    student: Student = Relationship(back_populates="follow_up_notes")
    teacher: Teacher = Relationship(back_populates="follow_up_notes")


# ---------- Assignments ----------


class Assignment(SQLModel, table=True):
    __tablename__ = "assignment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    class_subject_id: uuid.UUID = Field(
        foreign_key="class_subject.id", ondelete="CASCADE"
    )
    title: str = Field(max_length=100)
    description: str | None = None
    max_score: float = Field(default=10.0)
    due_date: date
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, server_default=func.now()
        ),
    )

    class_subject: ClassSubject = Relationship(back_populates="assignments")
    student_assignments: list["StudentAssignment"] = Relationship(
        back_populates="assignment"
    )


class StudentAssignment(SQLModel, table=True):
    __tablename__ = "student_assignment"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    assignment_id: uuid.UUID = Field(
        foreign_key="assignment.id", ondelete="CASCADE"
    )
    student_id: str = Field(
        foreign_key="student.id", ondelete="CASCADE", max_length=10
    )
    status: AssignmentStatus = Field(
        default=AssignmentStatus.pending,
        sa_type=Enum(
            AssignmentStatus,
            name="assignment_status",
            values_callable=lambda e: [m.value for m in e],
        ),
    )
    score: float | None = None
    submitted_at: datetime | None = None
    teacher_comment: str | None = None

    assignment: Assignment = Relationship(back_populates="student_assignments")
    student: Student = Relationship(back_populates="student_assignments")


# ---------- Engine & session ----------

engine = create_async_engine(settings.DATABASE_URL)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
