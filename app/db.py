import enum
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


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


# ---------- People ----------


class Teacher(Base):
    __tablename__ = "teacher"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    photo = Column(String)

    homeroom_classrooms = relationship("Classroom", back_populates="teacher")
    class_subjects = relationship("ClassSubject", back_populates="teacher")
    attendance_sessions = relationship("AttendanceSession", back_populates="teacher")


class Student(Base):
    __tablename__ = "student"

    id = Column(String(10), primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    nickname = Column(String(15), nullable=False)
    sex = Column(Enum(Sex, name="sex"), nullable=False)
    birth_date = Column(Date, nullable=False)
    photo = Column(String, nullable=True)

    enrollments = relationship("Enrollment", back_populates="student")
    guardian_links = relationship("StudentGuardian", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")


class Guardian(Base):
    __tablename__ = "guardian"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(30), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(15), nullable=True)

    student_links = relationship("StudentGuardian", back_populates="guardian")


class StudentGuardian(Base):
    __tablename__ = "student_guardian"

    student_id = Column(
        String(10),
        ForeignKey("student.id", ondelete="CASCADE"),
        primary_key=True,
    )
    guardian_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardian.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation = Column(String, nullable=False)
    is_primary = Column(Boolean, nullable=False)

    student = relationship("Student", back_populates="guardian_links")
    guardian = relationship("Guardian", back_populates="student_links")


# ---------- School structure ----------


class Subject(Base):
    __tablename__ = "subject"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), nullable=False, unique=True)
    name = Column(String(50), nullable=False)

    class_subjects = relationship("ClassSubject", back_populates="subject")


class Classroom(Base):
    __tablename__ = "classroom"
    __table_args__ = (UniqueConstraint("grade", "section", "academic_year"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homeroom_teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teacher.id", ondelete="RESTRICT"),
        nullable=False,
    )
    grade = Column(Integer, nullable=False)
    section = Column(Integer, nullable=False)
    academic_year = Column(Integer, nullable=False)
    room = Column(String(10), nullable=True)

    teacher = relationship("Teacher", back_populates="homeroom_classrooms")
    enrollments = relationship("Enrollment", back_populates="classroom")
    class_subjects = relationship("ClassSubject", back_populates="classroom")


class Enrollment(Base):
    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("student_id", "classroom_id"),
        UniqueConstraint("classroom_id", "student_in_class_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        String(10),
        ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
    )
    classroom_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_in_class_number = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)

    student = relationship("Student", back_populates="enrollments")
    classroom = relationship("Classroom", back_populates="enrollments")


class ClassSubject(Base):
    __tablename__ = "class_subject"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classroom_id = Column(
        UUID(as_uuid=True),
        ForeignKey("classroom.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subject.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teacher.id", ondelete="RESTRICT"),
        nullable=False,
    )
    term = Column(Integer, nullable=False)

    classroom = relationship("Classroom", back_populates="class_subjects")
    subject = relationship("Subject", back_populates="class_subjects")
    teacher = relationship("Teacher", back_populates="class_subjects")
    timetables = relationship("Timetable", back_populates="class_subject")


class Timetable(Base):
    __tablename__ = "timetable"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 1 AND 5"),  # 1=Mon ... 5=Fri
        CheckConstraint("end_time > start_time"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("class_subject.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String(10))

    class_subject = relationship("ClassSubject", back_populates="timetables")
    attendance_sessions = relationship("AttendanceSession", back_populates="timetable")


# ---------- Attendance ----------


class AttendanceSession(Base):
    __tablename__ = "attendance_session"
    __table_args__ = (UniqueConstraint("timetable_id", "date"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timetable_id = Column(
        UUID(as_uuid=True),
        ForeignKey("timetable.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teacher.id", ondelete="RESTRICT"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    timetable = relationship("Timetable", back_populates="attendance_sessions")
    teacher = relationship("Teacher", back_populates="attendance_sessions")
    attendances = relationship("Attendance", back_populates="session")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attendance_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id = Column(
        String(10),
        ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        Enum(Status, name="status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    note = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session = relationship("AttendanceSession", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")


# ---------- Engine & session ----------

engine = create_async_engine(settings.DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
