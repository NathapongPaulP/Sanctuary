from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db import Sex, AssignmentStatus
from datetime import date, datetime, time


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
    homeroom_teacher_id: UUID


class ClassroomCreate(ClassroomBase):
    homeroom_teacher_id: UUID


class EnrollmentBase(BaseModel):
    student_id: str
    student_in_class_number: int = Field(ge=1, description="เลขที่ของนักเรียนในห้อง")
    start_date: date = Field(default_factory=date.today, description="วันที่เริ่มเข้าเรียน")
    end_date: date | None = None


class EnrollmentCreate(EnrollmentBase):
    classroom_id: UUID


class EnrollmentRead(EnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    classroom_id: UUID
    student_id: str


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


class AssignmentBase(BaseModel):
    class_subject_id: UUID
    title: str
    description: str | None = None
    max_score: float = 10.0
    due_date: date


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentRead(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class StudentAssignmentBase(BaseModel):
    assignment_id: UUID
    student_id: str
    status: AssignmentStatus = AssignmentStatus.pending
    score: float | None = None
    submitted_at: datetime | None = None
    teacher_comment: str | None = None


class StudentAssignmentCreate(StudentAssignmentBase):
    pass


class StudentAssignmentUpdate(BaseModel):
    status: AssignmentStatus | None = None
    score: float | None = None
    submitted_at: datetime | None = None
    teacher_comment: str | None = None


class StudentAssignmentRead(StudentAssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class NextSession(BaseModel):
    day: int = Field(ge=1, le=5)
    start_time: time
    is_today: bool


class ClassPageData(BaseModel):
    """
    TODO: worksheet
    current_worksheet: str
    worksheet_missing: int
    worksheet_waiting_to_be_grade: int
    attention_required: AttentionRequired
    """

    class_subject_id: UUID
    classroom_id: UUID
    grade: int
    section: int
    academic_year: int
    number_of_students: int
    next_session: NextSession | None = None
    subject: str
    students_to_follow_up: int = 0


class TeacherAppropriateData(BaseModel):
    homeroom_class: list[ClassPageData] | None = None
    teaching_class: list[ClassPageData]


class CardData(BaseModel):
    teacher_id: UUID
    teacher_appropriate_data: TeacherAppropriateData
