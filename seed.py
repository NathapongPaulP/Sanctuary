"""
Wipe the database and fill it with realistic fake data.

    uv run python seed.py

- 21 classrooms (ป.1-ป.3: 4 sections, ป.4-ป.6: 3 sections), ~35 students each
- Each room has its own homeroom teacher. In ป.1-ป.3 they teach ภาษาไทย and
  คณิตศาสตร์ in their room (sometimes one more subject); in ป.4-ป.6 at least one
  core subject. The grade's other homeroom subjects are shared among its homeroom
  teachers; specialists cover English, PE and art. Every teacher has 20-25 periods.
- Clash-free weekly timetable (no teacher or room double-booked)
- Attendance for the last 20 school days, decided per student per day: ขาด and
  ลาป่วย cover the whole day (ลาป่วย often runs 2-3 days), สาย only the first
  period. 1-3 students per room start missing school in the last 1-2 weeks.
- A few students transferred out mid-term and a few transferred in recently
- Ids come from the seeded generator, so every run gives the same ids
"""

import asyncio
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
    FollowUpNote,
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
ATTENDANCE_DAYS = 20  # how many past school days get attendance records
TZ = ZoneInfo("Asia/Bangkok")

SECTIONS_PER_GRADE = {1: 4, 2: 4, 3: 4, 4: 3, 5: 3, 6: 3}
STUDENTS_PER_ROOM = (33, 37)
AT_RISK_PER_ROOM = (1, 3)
TRANSFER_ROOMS = 4  # rooms with a student moving out, and as many with one moving in
TRANSFER_OUT_DAYS_AGO = (5, 12)  # school days
TRANSFER_IN_DAYS_AGO = (2, 4)
# subjects taught by the grade's homeroom teachers; the rest go to specialists
HOMEROOM_SUBJECTS = ["thai", "math", "science", "social", "history", "career"]
CORE_SUBJECTS = ["thai", "math", "science", "social"]
SPECIALIST_SUBJECTS = ["english", "pe", "art"]
TARGET_LOAD = 22  # periods per week a specialist aims for
MIN_LOAD, MAX_LOAD = 20, 25

PERIODS = [
    (time(8, 30), time(9, 20)),
    (time(9, 20), time(10, 10)),
    (time(10, 20), time(11, 10)),
    (time(11, 10), time(12, 0)),
    (time(13, 0), time(13, 50)),
    (time(13, 50), time(14, 40)),
]
SLOTS = [(day, p) for day in range(1, 6) for p in range(len(PERIODS))]

# key: (code prefix, name, periods per week)
SUBJECTS = {
    "thai": ("ท", "ภาษาไทย", 5),
    "math": ("ค", "คณิตศาสตร์", 5),
    "science": ("ว", "วิทยาศาสตร์และเทคโนโลยี", 4),
    "social": ("ส", "สังคมศึกษา ศาสนา และวัฒนธรรม", 3),
    "history": ("ส", "ประวัติศาสตร์", 2),
    "pe": ("พ", "สุขศึกษาและพลศึกษา", 3),
    "art": ("ศ", "ศิลปะ", 2),
    "career": ("ง", "การงานอาชีพ", 2),
    "english": ("อ", "ภาษาอังกฤษ", 4),
}
# subjects sharing a code prefix need different course numbers
CODE_SUFFIX = {"history": "102"}

MALE_NAMES = [
    "ก้องภพ",
    "ชยพล",
    "ธนกฤต",
    "ภูมิพัฒน์",
    "ณัฐวุฒิ",
    "ปัณณวิชญ์",
    "กิตติพัฒน์",
    "ศุภกร",
    "วรเมธ",
    "พีรพัฒน์",
    "ธีรภัทร",
    "ภาคิน",
    "อชิรวิชญ์",
    "ปกรณ์",
    "สิรวิชญ์",
    "รัชชานนท์",
    "กันตพงศ์",
    "ณภัทร",
    "ธนวัฒน์",
    "จิรายุ",
]
FEMALE_NAMES = [
    "ณัฐธิดา",
    "พิมพ์ชนก",
    "กัญญาณัฐ",
    "ปุณยวีร์",
    "ชนัญชิดา",
    "ธัญชนก",
    "อรปรียา",
    "ภัทรธิดา",
    "สุพิชญา",
    "วรัญญา",
    "ณิชาภัทร",
    "กานต์ธิดา",
    "ปภาวรินทร์",
    "ศิริกานดา",
    "พิชชาพร",
    "รินรดา",
    "ชญาดา",
    "อัญชิสา",
    "มนัสนันท์",
    "ญาณิศา",
]
MALE_NICKNAMES = ["พีท", "เจได", "ภูมิ", "ต้นกล้า", "ไทม์", "ปัน", "กาย", "ออโต้", "ซัน", "ฟิวส์"]
FEMALE_NICKNAMES = [
    "มิ้นท์",
    "ข้าวหอม",
    "ใบเตย",
    "น้ำฝน",
    "แพรว",
    "ปาย",
    "เอิร์น",
    "ไข่มุก",
    "ฟ้า",
    "ขิม",
]
ADULT_MALE_NAMES = [
    "สมชาย",
    "ณัฐวุฒิ",
    "ประเสริฐ",
    "วีระพงษ์",
    "อนุชา",
    "สุรชัย",
    "ธนากร",
    "พงศกร",
    "ชาตรี",
    "วิชัย",
]
ADULT_FEMALE_NAMES = [
    "สุภาวดี",
    "สมหญิง",
    "วิมลรัตน์",
    "จันทร์เพ็ญ",
    "นงลักษณ์",
    "ปราณี",
    "รัตนา",
    "สุนิสา",
    "กาญจนา",
    "อรุณี",
]
LAST_NAMES = [
    "ดวงดี",
    "ตันติวงศ์",
    "ปิ่นทอง",
    "สมบูรณ์ชัย",
    "แก้วมณี",
    "สุวรรณรัตน์",
    "ศรีสุข",
    "ใจดี",
    "บุญมา",
    "วงศ์ใหญ่",
    "ทองคำ",
    "เพชรรัตน์",
    "ศักดิ์สิทธิ์",
    "รุ่งเรือง",
    "มั่นคง",
    "จันทร์หอม",
    "พรหมวงศ์",
    "ชัยมงคล",
    "อินทร์แก้ว",
    "นาคสวัสดิ์",
]
FOLLOW_UP_NOTES = [
    "โทรคุยกับผู้ปกครองแล้ว ผู้ปกครองรับทราบ",
    "คุยกับนักเรียน รับปากว่าจะมาให้ทัน",
    "นัดผู้ปกครองมาพบที่โรงเรียน",
    "ส่งข้อความแจ้งผู้ปกครองทางไลน์",
    "ส่งจดหมายแจ้งผู้ปกครอง",
    "ปรึกษาครูแนะแนวแล้ว",
    "เยี่ยมบ้านนักเรียน",
]
TABLES = [
    "follow_up_note",
    "attendance",
    "attendance_session",
    "timetable",
    "class_subject",
    "enrollment",
    "student_guardian",
    "guardian",
    "student",
    "classroom",
    "subject",
    "teacher",
]


def new_id():
    return uuid.UUID(int=random.getrandbits(128), version=4)


def make_teacher():
    if random.random() < 0.35:
        title, first = "นาย", random.choice(ADULT_MALE_NAMES)
    else:
        title, first = (
            random.choice(["นาง", "นางสาว"]),
            random.choice(ADULT_FEMALE_NAMES),
        )
    return {
        "id": new_id(),
        "title": title,
        "first_name": first,
        "last_name": random.choice(LAST_NAMES),
        "photo": None,
    }


def make_phone():
    return f"0{random.choice('689')}{random.randint(0, 9)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"


def build():
    data = defaultdict(list)
    school_days = last_school_days(ATTENDANCE_DAYS)

    # ---------- subjects ----------
    subject_id = {}  # (grade, key) -> id
    for grade in SECTIONS_PER_GRADE:
        for key, (prefix, name, _periods) in SUBJECTS.items():
            sid = new_id()
            subject_id[(grade, key)] = sid
            data["subject"].append(
                {
                    "id": sid,
                    "code": f"{prefix}1{grade}{CODE_SUFFIX.get(key, '101')}",
                    "name": f"{name} ป.{grade}",
                }
            )

    # ---------- classrooms, each with its own homeroom teacher ----------
    rooms = []  # dicts from data["classroom"]
    for grade, n_sections in SECTIONS_PER_GRADE.items():
        for section in range(1, n_sections + 1):
            teacher = make_teacher()
            data["teacher"].append(teacher)
            room = {
                "id": new_id(),
                "homeroom_teacher_id": teacher["id"],
                "grade": grade,
                "section": section,
                "academic_year": ACADEMIC_YEAR,
                "room": f"{grade}0{section}",
            }
            data["classroom"].append(room)
            rooms.append(room)

    # ---------- homeroom subjects: shared among the grade's homeroom teachers ----------
    teacher_for = {}  # (room id, key) -> teacher id
    for grade in SECTIONS_PER_GRADE:
        teacher_for.update(
            assign_homeroom_subjects([r for r in rooms if r["grade"] == grade])
        )

    # ---------- specialists: one subject each, rooms split evenly between them ----------
    for key in SPECIALIST_SUBJECTS:
        periods = SUBJECTS[key][2]
        n_teachers = max(1, round(len(rooms) * periods / TARGET_LOAD))
        teachers = [make_teacher() for _ in range(n_teachers)]
        data["teacher"].extend(teachers)
        for i, room in enumerate(rooms):
            teacher_for[(room["id"], key)] = teachers[i * n_teachers // len(rooms)][
                "id"
            ]

    # ---------- class subjects ----------
    lessons_by_room = defaultdict(
        list
    )  # room id -> [(class_subject row, periods, key)]
    for room in rooms:
        for key, (_prefix, _name, periods) in SUBJECTS.items():
            cs = {
                "id": new_id(),
                "classroom_id": room["id"],
                "subject_id": subject_id[(room["grade"], key)],
                "teacher_id": teacher_for[(room["id"], key)],
                "term": TERM,
            }
            data["class_subject"].append(cs)
            lessons_by_room[room["id"]].append((cs, periods, key))

    # ---------- timetable ----------
    data["timetable"] = build_timetable(rooms, lessons_by_room)

    # ---------- students, guardians, enrollments ----------
    next_seq = {}  # grade -> next running number for student ids
    enrollments_in = defaultdict(list)  # room id -> enrollment rows
    for grade, n_sections in SECTIONS_PER_GRADE.items():
        seq = 1
        for section in range(1, n_sections + 1):
            room = next(
                r for r in rooms if r["grade"] == grade and r["section"] == section
            )
            students = []
            for _ in range(random.randint(*STUDENTS_PER_ROOM)):
                students.append(make_student(grade, seq))
                seq += 1
            # Thai class numbers: boys first, then girls, each by first name
            students.sort(key=lambda s: (s["sex"] != Sex.M, s["first_name"]))
            for number, student in enumerate(students, start=1):
                enroll(data, enrollments_in, student, room, number, TERM_START)
        next_seq[grade] = seq

    # ---------- students who start missing school in the last 1-2 weeks ----------
    at_risk = {}  # student id -> (first bad day, status weights from then on)
    for room in rooms:
        for e in random.sample(
            enrollments_in[room["id"]], random.randint(*AT_RISK_PER_ROOM)
        ):
            late, absent = random.choice([(30, 10), (10, 30), (20, 20)])
            at_risk[e["student_id"]] = (
                school_days[-random.choice([5, 10])],
                [100 - late - absent - 3, late, absent, 2, 1],
            )

    # ---------- transfers: out mid-term, in recently ----------
    transfer_rooms = random.sample(rooms, TRANSFER_ROOMS * 2)
    for room in transfer_rooms[:TRANSFER_ROOMS]:
        regulars = [
            e for e in enrollments_in[room["id"]] if e["student_id"] not in at_risk
        ]
        random.choice(regulars)["end_date"] = school_days[
            -random.randint(*TRANSFER_OUT_DAYS_AGO)
        ]
    for room in transfer_rooms[TRANSFER_ROOMS:]:
        grade = room["grade"]
        student = make_student(grade, next_seq[grade])
        next_seq[grade] += 1
        number = len(enrollments_in[room["id"]]) + 1
        start = school_days[-random.randint(*TRANSFER_IN_DAYS_AGO)]
        enroll(data, enrollments_in, student, room, number, start)

    # ---------- attendance ----------
    build_attendance(data, school_days, at_risk)

    # ---------- follow-up notes for about half of the students who stand out ----------
    homeroom_of = {
        e["student_id"]: room["homeroom_teacher_id"]
        for room in rooms
        for e in enrollments_in[room["id"]]
    }
    for student_id, (risk_from, _weights) in at_risk.items():
        if random.random() < 0.5:
            add_follow_up_notes(
                data, student_id, homeroom_of[student_id], risk_from, school_days
            )
    return data


def add_follow_up_notes(data, student_id, teacher_id, risk_from, school_days):
    """1-2 notes on school days after the student started missing, in date order."""
    days = [d for d in school_days if d >= risk_from]
    now = datetime.now(TZ)
    for day in sorted(random.sample(days, random.randint(1, 2))):
        written = datetime.combine(
            day + timedelta(days=random.randint(0, 2)),
            time(random.randint(15, 19), random.randint(0, 59)),
            TZ,
        )
        data["follow_up_note"].append(
            {
                "id": new_id(),
                "student_id": student_id,
                "teacher_id": teacher_id,
                "action_date": day,
                "note": random.choice(FOLLOW_UP_NOTES),
                "created_at": min(written, now),
            }
        )


def make_student(grade, seq):
    id_prefix = str(ACADEMIC_YEAR - 2500 - (grade - 1))  # year they entered ป.1
    sex = random.choice([Sex.M, Sex.F])
    male = sex == Sex.M
    return {
        "id": f"{id_prefix}{seq:03d}",
        "first_name": random.choice(MALE_NAMES if male else FEMALE_NAMES),
        "last_name": random.choice(LAST_NAMES),
        "nickname": random.choice(MALE_NICKNAMES if male else FEMALE_NICKNAMES),
        "sex": sex,
        "birth_date": date(2020 - grade, 1, 1) + timedelta(days=random.randint(0, 364)),
        "photo": None,
    }


def enroll(data, enrollments_in, student, room, number, start):
    data["student"].append(student)
    enrollment = {
        "id": new_id(),
        "student_id": student["id"],
        "classroom_id": room["id"],
        "student_in_class_number": number,
        "start_date": start,
        "end_date": None,
    }
    data["enrollment"].append(enrollment)
    enrollments_in[room["id"]].append(enrollment)
    add_guardians(data, student)


def assign_homeroom_subjects(grade_rooms, attempts=200):
    """Homeroom teachers keep their core subjects; the grade's other homeroom lessons
    go to the least-loaded homeroom teacher of another room. Retry until every load
    is within MIN_LOAD..MAX_LOAD."""
    for _ in range(attempts):
        teacher_for, load, rest = {}, defaultdict(int), []
        for room in grade_rooms:
            if room["grade"] <= 3:
                others = [k for k in HOMEROOM_SUBJECTS if k not in ("thai", "math")]
                own = ["thai", "math"] + random.sample(others, random.randint(0, 1))
            else:
                own = random.sample(CORE_SUBJECTS, random.randint(1, 2))
            for key in HOMEROOM_SUBJECTS:
                if key in own:
                    teacher_for[(room["id"], key)] = room["homeroom_teacher_id"]
                    load[room["homeroom_teacher_id"]] += SUBJECTS[key][2]
                else:
                    rest.append((room, key))

        random.shuffle(rest)
        rest.sort(key=lambda lesson: -SUBJECTS[lesson[1]][2])  # biggest first
        for room, key in rest:
            teachers = [r["homeroom_teacher_id"] for r in grade_rooms if r is not room]
            teacher_id = min(teachers, key=lambda t: (load[t], random.random()))
            teacher_for[(room["id"], key)] = teacher_id
            load[teacher_id] += SUBJECTS[key][2]

        if all(
            MIN_LOAD <= load[r["homeroom_teacher_id"]] <= MAX_LOAD for r in grade_rooms
        ):
            return teacher_for
    raise RuntimeError("could not balance homeroom teacher loads")


def add_guardians(data, student):
    last = student["last_name"]
    parents = [("บิดา", "นาย", ADULT_MALE_NAMES), ("มารดา", "นาง", ADULT_FEMALE_NAMES)]
    random.shuffle(parents)
    count = 2 if random.random() < 0.4 else 1
    for i, (relation, title, names) in enumerate(parents[:count]):
        guardian = {
            "id": new_id(),
            "title": title,
            "first_name": random.choice(names),
            "last_name": last,
            "phone": make_phone() if random.random() < 0.85 else None,
        }
        data["guardian"].append(guardian)
        data["student_guardian"].append(
            {
                "student_id": student["id"],
                "guardian_id": guardian["id"],
                "relation": relation,
                "is_primary": i == 0,
            }
        )


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
        [
            [s for s in SLOTS if s not in teacher_busy[cs["teacher_id"]]]
            for cs, _key in queue
        ]
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
        rows.append(
            {
                "id": new_id(),
                "class_subject_id": cs["id"],
                "day_of_the_week": day,
                "start_time": start,
                "end_time": end,
                "room": "สนาม" if key == "pe" else room["room"],
                "_teacher_id": cs["teacher_id"],
                "_classroom_id": room["id"],
            }
        )
    return rows


def last_school_days(n):
    days, d = [], datetime.now(TZ).date()
    while len(days) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    return sorted(days)


NORMAL_WEIGHTS = [
    96,
    1.5,
    0.5,
    1.5,
    0.5,
]  # present, late, absent, sick leave, personal leave
STATUSES = [
    Status.present,
    Status.late,
    Status.absent,
    Status.sick_leave,
    Status.personal_leave,
]


def daily_statuses(e, school_days, at_risk):
    """One status per school day the student is enrolled; sick leave runs 1-3 days."""
    risk_from, risk_weights = at_risk.get(e["student_id"], (None, None))
    statuses, sick_days_left = {}, 0
    for day in school_days:
        if e["start_date"] > day or (e["end_date"] and e["end_date"] < day):
            continue
        if sick_days_left:
            status, sick_days_left = Status.sick_leave, sick_days_left - 1
        else:
            weights = risk_weights if risk_from and day >= risk_from else NORMAL_WEIGHTS
            status = random.choices(STATUSES, weights)[0]
            if status == Status.sick_leave:
                sick_days_left = random.choice([0, 1, 1, 2])
        statuses[day] = status
    return statuses


def build_attendance(data, school_days, at_risk):
    enrollments_in = defaultdict(list)
    status_on = {}  # (student id, day) -> status for the whole day
    for e in data["enrollment"]:
        enrollments_in[e["classroom_id"]].append(e)
        for day, status in daily_statuses(e, school_days, at_risk).items():
            status_on[(e["student_id"], day)] = status

    first_period = PERIODS[0][0]
    for day in school_days:
        for slot in data["timetable"]:
            if slot["day_of_the_week"] != day.isoweekday():
                continue
            recorded = datetime.combine(day, slot["end_time"], TZ) - timedelta(
                minutes=random.randint(0, 20)
            )
            session = {
                "id": new_id(),
                "timetable_id": slot["id"],
                "teacher_id": slot["_teacher_id"],
                "date": day,
                "recorded_at": recorded,
            }
            data["attendance_session"].append(session)
            for e in enrollments_in[slot["_classroom_id"]]:
                student_id = e["student_id"]
                status = status_on.get((student_id, day))
                if status is None:  # not enrolled that day
                    continue
                if status == Status.late and slot["start_time"] != first_period:
                    status = Status.present
                data["attendance"].append(
                    {
                        "id": new_id(),
                        "session_id": session["id"],
                        "student_id": student_id,
                        "status": status,
                        "note": "ไข้หวัด" if status == Status.sick_leave else None,
                        "updated_at": recorded,
                    }
                )


MODELS = [
    Teacher,
    Subject,
    Classroom,
    Student,
    Guardian,
    StudentGuardian,
    Enrollment,
    ClassSubject,
    Timetable,
    AttendanceSession,
    Attendance,
    FollowUpNote,
]


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
                await session.exec(insert(model), params=rows[i : i + 5000])
        await session.commit()

    for model in MODELS:
        print(f"{model.__tablename__:<20} {len(data[model.__tablename__])}")


if __name__ == "__main__":
    asyncio.run(main())
