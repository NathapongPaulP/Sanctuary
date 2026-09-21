from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db import Sex, Status
from datetime import date, datetime


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    nickname: str
    sex: Sex
    photo: str | None = None


class StudentCreate(StudentBase):
    birth_date: date # PDPA


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
    homeroom_teacher: TeacherRead


class ClassroomCreate(ClassroomBase):
    homeroom_teacher_id: UUID