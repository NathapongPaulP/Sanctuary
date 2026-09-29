"""
Wipe the database and fill it with realistic fake data.

    uv run python seed.py

- 21 classrooms (ป.1-ป.3: 4 sections, ป.4-ป.6: 3 sections), ~35 students each
- Every teacher teaches exactly one subject, across several rooms
- 21 of them are also homeroom teacher of one of the rooms they teach
- Clash-free weekly timetable (no teacher or room double-booked)
- Attendance for the last few school days
"""

import asyncio
import math
import random
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import insert, text

from app.db import (
    Attendance,
    AttendanceSession,
    Classroom,
    ClassSubject,
    Enrollment,
    Guardian,
    Sex,
    Status,
    Student,
    StudentGuardian,
    Subject,
    Teacher,
    Timetable,
    async_session_maker,
)

random.seed(42)

ACADEMIC_YEAR = 2569
TERM = 1
TERM_START = date(2026, 5, 18)
ATTENDANCE_DAYS = 3  # how many past school days get attendance records
TZ = ZoneInfo("Asia/Bangkok")

SECTIONS_PER_GRADE = {1: 4, 2: 4, 3: 4, 4: 3, 5: 3, 6: 3}
STUDENTS_PER_ROOM = (33, 37)

PERIODS = [
    (time(8, 30), time(9, 20)),
    (time(9, 20), time(10, 10)),
    (time(10, 20), time(11, 10)),
    (time(11, 10), time(12, 0)),
    (time(13, 0), time(13, 50)),
    (time(13, 50), time(14, 40)),
]
SLOTS = [(day, p) for day in range(1, 6) for p in range(len(PERIODS))]

# key: (code prefix, name, periods per week, max rooms per teacher)
SUBJECTS = {
    "thai": ("ท", "ภาษาไทย", 5, 4),
    "math": ("ค", "คณิตศาสตร์", 5, 4),
    "science": ("ว", "วิทยาศาสตร์และเทคโนโลยี", 4, 5),
    "social": ("ส", "สังคมศึกษา ศาสนา และวัฒนธรรม", 3, 7),
    "history": ("ส", "ประวัติศาสตร์", 2, 10),
    "pe": ("พ", "สุขศึกษาและพลศึกษา", 3, 7),
    "art": ("ศ", "ศิลปะ", 2, 10),
    "career": ("ง", "การงานอาชีพ", 2, 10),
    "english": ("อ", "ภาษาอังกฤษ", 4, 5),
}
# subjects sharing a code prefix need different course numbers
CODE_SUFFIX = {"history": "102"}

MALE_NAMES = [
    "ก้องภพ", "ชยพล", "ธนกฤต", "ภูมิพัฒน์", "ณัฐวุฒิ", "ปัณณวิชญ์", "กิตติพัฒน์",
    "ศุภกร", "วรเมธ", "พีรพัฒน์", "ธีรภัทร", "ภาคิน", "อชิรวิชญ์", "ปกรณ์",
    "สิรวิชญ์", "รัชชานนท์", "กันตพงศ์", "ณภัทร", "ธนวัฒน์", "จิรายุ",
]
FEMALE_NAMES = [
    "ณัฐธิดา", "พิมพ์ชนก", "กัญญาณัฐ", "ปุณยวีร์", "ชนัญชิดา", "ธัญชนก", "อรปรียา",
    "ภัทรธิดา", "สุพิชญา", "วรัญญา", "ณิชาภัทร", "กานต์ธิดา", "ปภาวรินทร์",
    "ศิริกานดา", "พิชชาพร", "รินรดา", "ชญาดา", "อัญชิสา", "มนัสนันท์", "ญาณิศา",
]
MALE_NICKNAMES = ["พีท", "เจได", "ภูมิ", "ต้นกล้า", "ไทม์", "ปัน", "กาย", "ออโต้", "ซัน", "ฟิวส์"]
FEMALE_NICKNAMES = ["มิ้นท์", "ข้าวหอม", "ใบเตย", "น้ำฝน", "แพรว", "ปาย", "เอิร์น", "ไข่มุก", "ฟ้า", "ขิม"]
ADULT_MALE_NAMES = ["สมชาย", "ณัฐวุฒิ", "ประเสริฐ", "วีระพงษ์", "อนุชา", "สุรชัย", "ธนากร", "พงศกร", "ชาตรี", "วิชัย"]
ADULT_FEMALE_NAMES = ["สุภาวดี", "สมหญิง", "วิมลรัตน์", "จันทร์เพ็ญ", "นงลักษณ์", "ปราณี", "รัตนา", "สุนิสา", "กาญจนา", "อรุณี"]
LAST_NAMES = [
    "ดวงดี", "ตันติวงศ์", "ปิ่นทอง", "สมบูรณ์ชัย", "แก้วมณี", "สุวรรณรัตน์", "ศรีสุข",
    "ใจดี", "บุญมา", "วงศ์ใหญ่", "ทองคำ", "เพชรรัตน์", "ศักดิ์สิทธิ์", "รุ่งเรือง",
    "มั่นคง", "จันทร์หอม", "พรหมวงศ์", "ชัยมงคล", "อินทร์แก้ว", "นาคสวัสดิ์",
]
TABLES = [
    "attendance", "attendance_session", "timetable", "class_subject", "enrollment",
    "student_guardian", "guardian", "student", "classroom", "subject", "teacher",
]


def new_id():
    return uuid.uuid4()


def make_teacher():
    if random.random() < 0.35:
        title, first = "นาย", random.choice(ADULT_MALE_NAMES)
    else:
        title, first = random.choice(["นาง", "นางสาว"]), random.choice(ADULT_FEMALE_NAMES)
    return {"id": new_id(), "title": title, "first_name": first,
            "last_name": random.choice(LAST_NAMES), "photo": None}


def make_phone():
    return f"0{random.choice('689')}{random.randint(0, 9)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"


def build():
    data = defaultdict(list)

    # ---------- subjects ----------
    subject_id = {}  # (grade, key) -> id
    for grade in SECTIONS_PER_GRADE:
        for key, (prefix, name, _periods, _max_rooms) in SUBJECTS.items():
            sid = new_id()
            subject_id[(grade, key)] = sid
            data["subject"].append({
                "id": sid,
                "code": f"{prefix}1{grade}{CODE_SUFFIX.get(key, '101')}",
                "name": f"{name} ป.{grade}",
            })

    # ---------- classrooms (homeroom teacher is picked further down) ----------
    rooms = []  # dicts from data["classroom"]
    for grade, n_sections in SECTIONS_PER_GRADE.items():
        for section in range(1, n_sections + 1):
            room = {"id": new_id(), "homeroom_teacher_id": None, "grade": grade,
                    "section": section, "academic_year": ACADEMIC_YEAR,
                    "room": f"{grade}0{section}"}
            data["classroom"].append(room)
            rooms.append(room)

    # ---------- teachers: one subject each, rooms split evenly between them ----------
    teacher_for = {}  # (room id, key) -> teacher id
    for key, (_prefix, _name, _periods, max_rooms) in SUBJECTS.items():
        n_teachers = math.ceil(len(rooms) / max_rooms)
        teachers = [make_teacher() for _ in range(n_teachers)]
        data["teacher"].extend(teachers)
        for i, room in enumerate(rooms):
            teacher_for[(room["id"], key)] = teachers[i * n_teachers // len(rooms)]["id"]

    # ---------- class subjects ----------
    lessons_by_room = defaultdict(list)  # room id -> [(class_subject row, periods, key)]
    for room in rooms:
        for key, (_prefix, _name, periods, _max_rooms) in SUBJECTS.items():
            cs = {"id": new_id(), "classroom_id": room["id"],
                  "subject_id": subject_id[(room["grade"], key)],
                  "teacher_id": teacher_for[(room["id"], key)], "term": TERM}
            data["class_subject"].append(cs)
            lessons_by_room[room["id"]].append((cs, periods, key))

    # ---------- homeroom: each room gets a different teacher who teaches in it ----------
    teachers_in = [[cs["teacher_id"] for cs, _p, _k in lessons_by_room[r["id"]]] for r in rooms]
    for i, teacher_id in bipartite_match(teachers_in).items():
        rooms[i]["homeroom_teacher_id"] = teacher_id

    # ---------- timetable ----------
    data["timetable"] = build_timetable(rooms, lessons_by_room)

    # ---------- students, guardians, enrollments ----------
    for grade, n_sections in SECTIONS_PER_GRADE.items():
        id_prefix = str(ACADEMIC_YEAR - 2500 - (grade - 1))  # year they entered ป.1
        seq = 1
        for section in range(1, n_sections + 1):
            room = next(r for r in rooms if r["grade"] == grade and r["section"] == section)
            students = []
            for _ in range(random.randint(*STUDENTS_PER_ROOM)):
                sex = random.choice([Sex.M, Sex.F])
                male = sex == Sex.M
                students.append({
                    "id": f"{id_prefix}{seq:03d}",
                    "first_name": random.choice(MALE_NAMES if male else FEMALE_NAMES),
                    "last_name": random.choice(LAST_NAMES),
                    "nickname": random.choice(MALE_NICKNAMES if male else FEMALE_NICKNAMES),
                    "sex": sex,
                    "birth_date": date(2020 - grade, 1, 1) + timedelta(days=random.randint(0, 364)),
                    "photo": None,
                })
                seq += 1
            # Thai class numbers: boys first, then girls, each by first name
            students.sort(key=lambda s: (s["sex"] != Sex.M, s["first_name"]))
            for number, student in enumerate(students, start=1):
                data["student"].append(student)
                data["enrollment"].append({
                    "id": new_id(), "student_id": student["id"], "classroom_id": room["id"],
                    "student_in_class_number": number, "start_date": TERM_START, "end_date": None,
                })
                add_guardians(data, student)

    # ---------- attendance ----------
    build_attendance(data)
    return data


def add_guardians(data, student):
    last = student["last_name"]
    parents = [("บิดา", "นาย", ADULT_MALE_NAMES), ("มารดา", "นาง", ADULT_FEMALE_NAMES)]
    random.shuffle(parents)
    count = 2 if random.random() < 0.4 else 1
    for i, (relation, title, names) in enumerate(parents[:count]):
        guardian = {"id": new_id(), "title": title, "first_name": random.choice(names),
                    "last_name": last, "phone": make_phone() if random.random() < 0.85 else None}
        data["guardian"].append(guardian)
        data["student_guardian"].append({"student_id": student["id"], "guardian_id": guardian["id"],
                                         "relation": relation, "is_primary": i == 0})


def build_timetable(rooms, lessons_by_room, attempts=200):
    """Fill every room's 30 slots with no teacher double-booked; restart if a room gets stuck."""
    for _ in range(attempts):
        teacher_busy = defaultdict(set)
        rows = []
        for room in random.sample(rooms, len(rooms)):
            placed = place_room(room, lessons_by_room[room["id"]], teacher_busy)
            if placed is None:
                break
            rows.extend(placed)
        else:
            return rows
    raise RuntimeError("could not build a clash-free timetable")


def bipartite_match(options):
    """options[i] = choices for item i. Give every item a different choice, or None if impossible."""
    options = [random.sample(o, len(o)) for o in options]
    owner = {}  # choice -> item index

    def assign(i, seen):
        for choice in options[i]:
            if choice in seen:
                continue
            seen.add(choice)
            if choice not in owner or assign(owner[choice], seen):
                owner[choice] = i
                return True
        return False

    if not all(assign(i, set()) for i in range(len(options))):
        return None
    return {i: choice for choice, i in owner.items()}


def match_periods(queue, teacher_busy):
    """Assign each period to its own slot where its teacher is free."""
    return bipartite_match(
        [[s for s in SLOTS if s not in teacher_busy[cs["teacher_id"]]] for cs, _key in queue]
    )


def place_room(room, lessons, teacher_busy, tries=30):
    queue = [(cs, key) for cs, periods, key in lessons for _ in range(periods)]

    # try several matchings, keep the one where subjects repeat on the same day the least
    best, best_repeats = None, None
    for _ in range(tries):
        match = match_periods(queue, teacher_busy)
        if match is None:
            return None
        days = [(queue[i][0]["id"], slot[0]) for i, slot in match.items()]
        repeats = len(days) - len(set(days))
        if best is None or repeats < best_repeats:
            best, best_repeats = match, repeats
        if repeats == 0:
            break

    placed = [(queue[i][0], slot, queue[i][1]) for i, slot in best.items()]
    for cs, slot, _key in placed:
        teacher_busy[cs["teacher_id"]].add(slot)

    rows = []
    for cs, (day, period), key in placed:
        start, end = PERIODS[period]
        rows.append({"id": new_id(), "class_subject_id": cs["id"], "day_of_the_week": day,
                     "start_time": start, "end_time": end,
                     "room": "สนาม" if key == "pe" else room["room"],
                     "_teacher_id": cs["teacher_id"], "_classroom_id": room["id"]})
    return rows


def last_school_days(n):
    days, d = [], datetime.now(TZ).date()
    while len(days) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    return sorted(days)


def build_attendance(data):
    students_in = defaultdict(list)
    for e in data["enrollment"]:
        students_in[e["classroom_id"]].append(e["student_id"])

    statuses = [Status.present, Status.late, Status.absent, Status.sick_leave, Status.personal_leave]
    weights = [90, 4, 3, 2, 1]
    for day in last_school_days(ATTENDANCE_DAYS):
        for slot in data["timetable"]:
            if slot["day_of_the_week"] != day.isoweekday():
                continue
            recorded = datetime.combine(day, slot["end_time"], TZ) - timedelta(minutes=random.randint(0, 20))
            session = {"id": new_id(), "timetable_id": slot["id"], "teacher_id": slot["_teacher_id"],
                       "date": day, "recorded_at": recorded}
            data["attendance_session"].append(session)
            for student_id in students_in[slot["_classroom_id"]]:
                status = random.choices(statuses, weights)[0]
                data["attendance"].append({
                    "id": new_id(), "session_id": session["id"], "student_id": student_id,
                    "status": status, "note": "ไข้หวัด" if status == Status.sick_leave else None,
                    "updated_at": recorded,
                })


MODELS = [Teacher, Subject, Classroom, Student, Guardian, StudentGuardian, Enrollment,
          ClassSubject, Timetable, AttendanceSession, Attendance]


async def main():
    data = build()
    for row in data["timetable"]:  # helper keys, not real columns
        row.pop("_teacher_id")
        row.pop("_classroom_id")

    async with async_session_maker() as session:
        await session.exec(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))
        for model in MODELS:  # parents before children
            rows = data[model.__tablename__]
            for i in range(0, len(rows), 5000):
                await session.exec(insert(model), params=rows[i:i + 5000])
        await session.commit()

    for model in MODELS:
        print(f"{model.__tablename__:<20} {len(data[model.__tablename__])}")


if __name__ == "__main__":
    asyncio.run(main())
