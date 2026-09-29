from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import class_card, class_subjects, teachers, students, classrooms, enrollments, subjects, time_tables


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
app.include_router(class_card.router)
