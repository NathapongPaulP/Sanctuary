from collections.abc import AsyncGenerator
import uuid

import enum
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Integer,
    func,
    Boolean,
    Enum,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


class Sex(str, enum.Enum):
    M = "M"
    F = "F"


class Status(str, enum.Enum):
    present = "มา"
    absent = "ลา"
    late = "สาย"
    sick_leave = "ลาป่วย"
    personal_leave = "ลากิจ"


class Student(Base):
    __tablename__ = "student"

    id = Column(String(10), primary_key=True, unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    nickname = Column(String(15), nullable=False)
    sex = Column(Enum(Sex, name="sex"), nullable=False)
    birth_date = Column(Date, nullable=False)
    photo = Column(String, nullable=True)

    enrollment = relationship("Enrollment", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    guardian_links = relationship("StudentGuardian", back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollment"

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
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)

    student = relationship("Student", back_populates="enrollment")
    classroom = relationship("Classroom", back_populates="enrollment")


class Teacher(Base):
    __tablename__ = "teacher"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    photo = Column(String)

    attendance_sessions = relationship("AttendanceSession", back_populates="teacher")
    homeroom_classrooms = relationship("Classroom", back_populates="teacher")
    class_subjects = relationship("ClassSubject", back_populates="teacher")


class Timetable(Base):
    __tablename__ = "timetable"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_subject_id = Column(
        UUID(as_uuid=True),
        ForeignKey("class_subject.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    room = Column(String(10))

    class_subject = relationship("ClassSubject", back_populates="timetables")
    attendance_sessions = relationship("AttendanceSession", back_populates="timetable")


class AttendanceSession(Base):
    __tablename__ = "attendance_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timetable_id = Column(
        UUID(as_uuid=True),
        ForeignKey("timetable.id", ondelete="CASCADE"),
        nullable=False
    )
    day = Column(Integer)
    teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teacher.id", ondelete="CASCADE"),
        nullable=False
    )
    recorded_at = Column(DateTime)

    timetable = relationship("Timetable", back_populates="attendance_sessions")
    teacher = relationship("Teacher", back_populates="attendance_sessions")
    attendances = relationship("Attendance", back_populates="session")


class Classroom(Base):
    __tablename__ = "classroom"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homeroom_teacher_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teacher.id", ondelete="CASCADE"),
        nullable=False
    )
    grade = Column(Integer, nullable=False)
    section = Column(Integer, nullable=False)
    academic_year = Column(Integer, nullable=False)
    room = Column(String(10), nullable=True)

    teacher = relationship("Teacher", back_populates="homeroom_classrooms")
    enrollment = relationship("Enrollment", back_populates="classroom")
    class_subjects = relationship("ClassSubject", back_populates="classroom")


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
        ForeignKey("teacher.id", ondelete="CASCADE"),
        nullable=False,
    )
    term = Column(Integer, nullable=False)

    classroom = relationship("Classroom", back_populates="class_subjects")
    subject = relationship("Subject", back_populates="class_subjects")
    teacher = relationship("Teacher", back_populates="class_subjects")
    timetables = relationship("Timetable", back_populates="class_subject")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("attendance_session.id", ondelete="CASCADE"),
        nullable=False
    )
    student_id = Column(
        String(10),
        ForeignKey("student.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(Enum(Status, name="status"), nullable=False)
    note = Column(String, nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session = relationship("AttendanceSession", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")


class Subject(Base):
    __tablename__ = "subject"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), nullable=False)
    name = Column(String(50), nullable=False)

    class_subjects = relationship("ClassSubject", back_populates="subject")


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
        nullable=False,
    )
    guardian_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardian.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    relation = Column(String, nullable=False)
    is_primary = Column(Boolean, nullable=False)

    student = relationship("Student", back_populates="guardian_links")
    guardian = relationship("Guardian", back_populates="student_links")


engine = create_async_engine(settings.DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
