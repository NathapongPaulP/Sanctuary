from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db import Sex
from datetime import date, time


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    nickname: str
    sex: Sex
    photo: str | None = None


class StudentCreate(StudentBase):
    id: str
    birth_date: date  # PDPA


class StudentRead(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class TeacherBase(BaseModel):
    first_name: str
    last_name: str
    title: str
    photo: str | None = None


class TeacherCreate(TeacherBase):
    pass


class TeacherRead(TeacherBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ClassroomBase(BaseModel):
    grade: int = Field(ge=1, le=6)
    section: int = Field(ge=1)
    academic_year: int = Field(ge=2500, le=2700)
    room: str | None = None


class ClassroomRead(ClassroomBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    teacher: TeacherRead


class ClassroomCreate(ClassroomBase):
    homeroom_teacher_id: UUID


class EnrollmentBase(BaseModel):
    student_in_class_number: int = Field(ge=1, description="เลขที่ของนักเรียนในห้อง")
    start_date: date = Field(
        default_factory=date.today, description="วันที่เริ่มเข้าเรียน"
    )
    end_date: date | None = None


class EnrollmentCreate(EnrollmentBase):
    student_id: str
    classroom_id: UUID


class EnrollmentRead(EnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_id: str
    classroom_id: UUID
    student: StudentRead


class SubjectBase(BaseModel):
    code: str
    name: str


class SubjectCreate(SubjectBase):
    pass


class SubjectRead(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ClassSubjectBase(BaseModel):
    classroom_id: UUID
    subject_id: UUID
    teacher_id: UUID
    term: int


class ClassSubjectCreate(ClassSubjectBase):
    pass


class ClassSubjectRead(ClassSubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class TimeTableBase(BaseModel):
    class_subject_id: UUID
    day_of_the_week: int
    start_time: time
    end_time: time
    room: str | None = None


class TimeTableCreate(TimeTableBase):
    pass


class TimeTableRead(TimeTableBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
