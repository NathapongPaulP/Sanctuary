import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import class_subjects, teachers, students, classrooms, enrollments, subjects, time_tables


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(classrooms.router)
app.include_router(enrollments.router)
app.include_router(subjects.router)
app.include_router(class_subjects.router)
app.include_router(time_tables.router)