"""Department Portal endpoints — full sovereign API for department heads/members."""
import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_permission


logger = logging.getLogger(__name__)
router = APIRouter()


def _any_in(column, param_name, values):
    # Generate database-agnostic SQL for matching a column against a list.
    # Returns (sql_fragment, params_dict).
    # PostgreSQL: column = ANY(:param_name) with list param
    # SQLite: column IN (:param_0, :param_1, ...) with individual params
    if not values:
        return "1=0", {}
    if settings.is_sqlite:
        placeholders = ", ".join([":" + param_name + "_" + str(i) for i in range(len(values))])
        params = {param_name + "_" + str(i): v for i, v in enumerate(values)}
        return column + " IN (" + placeholders + ")", params
    else:
        return column + " = ANY(:" + param_name + ")", {param_name: values}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ExamCreate(BaseModel):
    name: str
    description: str | None = None
    exam_date: str
    start_time: str | None = None
    end_time: str | None = None
    room_name: str | None = None
    max_score: float = 20
    status: str = "scheduled"
    class_id: str | None = None
    subject_id: str
    term_id: str


# ─── Helper: resolve department for current user ──────────────────────────────

def _get_user_department(db: Session, user_id: str, tenant_id: str) -> dict | None:
    """Find the department for the current user (head only — no separate members table).

    NOTE: The schema does not declare a `department_members` table; users are
    linked to a department only via `departments.head_id`. We intentionally do
    NOT query `department_members` here — doing so raised
    `sqlite3.OperationalError: no such table: department_members` on SQLite.
    """
    row = db.execute(text("""
        SELECT d.id, d.name, d.code, d.description
        FROM departments d
        WHERE d.tenant_id = :tenant_id AND d.head_id = :user_id
        LIMIT 1
    """), {"tenant_id": tenant_id, "user_id": user_id}).mappings().first()

    return dict(row) if row else None


def _get_department_classroom_ids(db: Session, department_id: str, tenant_id: str) -> list:
    rows = db.execute(text("""
        SELECT class_id FROM classroom_departments
        WHERE department_id = :dept_id AND tenant_id = :tenant_id
    """), {"dept_id": department_id, "tenant_id": tenant_id}).fetchall()
    return [str(r.class_id) for r in rows]


# ─── My Department ────────────────────────────────────────────────────────────

@router.get("/my-department/")
def get_my_department(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """Return the department associated with the current user."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")
        return dept
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error getting my department: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard/")
def department_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """
        Aggregate dashboard stats for the current user's department.
        Returns: department info, stats (students, teachers, subjects, attendance),
                 recent grade activity.
        """
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        department_id = dept["id"]
        class_ids = _get_department_classroom_ids(db, department_id, tenant_id)

        stats = {
            "totalStudents": 0,
            "totalTeachers": 0,
            "totalSubjects": 0,
            "attendanceRate": 0,
            "upcomingExams": 0,
            "pendingGrades": 0,
        }
        recent_activities = []

        if class_ids:
            cid_sql, cid_params = _any_in("e.class_id", "dcids", class_ids)
            tid_sql, tid_params = _any_in("ta.class_id", "tcids", class_ids)
            aid_sql, aid_params = _any_in("class_id", "acids", class_ids)

            # Students
            stats["totalStudents"] = db.execute(text(f"""
                SELECT COUNT(DISTINCT e.student_id) FROM enrollments e
                WHERE {cid_sql} AND e.status = 'active'
            """), {**cid_params}).scalar() or 0

            # Teachers
            stats["totalTeachers"] = db.execute(text(f"""
                SELECT COUNT(DISTINCT ta.teacher_id) FROM teacher_assignments ta
                WHERE {tid_sql} AND ta.tenant_id = :tenant_id
            """), {**tid_params, "tenant_id": tenant_id}).scalar() or 0

            # Subjects
            stats["totalSubjects"] = db.execute(text(f"""
                SELECT COUNT(DISTINCT ta.subject_id) FROM teacher_assignments ta
                WHERE {tid_sql} AND ta.tenant_id = :tenant_id
            """), {**tid_params, "tenant_id": tenant_id}).scalar() or 0

            # Attendance (last 30 days)
            thirty_ago = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
            att = db.execute(text(f"""
                SELECT status FROM attendance
                WHERE {aid_sql} AND date >= :since
            """), {**aid_params, "since": thirty_ago}).fetchall()
            total_att = len(att)
            present = sum(1 for a in att if a.status == "PRESENT")
            stats["attendanceRate"] = round((present / total_att) * 100) if total_att else 0

            # Upcoming exams
            today_str = datetime.date.today().isoformat()
            stats["upcomingExams"] = db.execute(text("""
                SELECT COUNT(*) FROM exams
                WHERE department_id = :dept_id AND exam_date >= :today AND status = 'scheduled'
            """), {"dept_id": department_id, "today": today_str}).scalar() or 0

            # Recent grades (last 5)
            grades = db.execute(text("""
                SELECT g.id, g.score, g.created_at,
                       s.first_name, s.last_name,
                       a.name AS assessment_name,
                       sub.name AS subject_name
                FROM grades g
                JOIN students s ON s.id = g.student_id
                JOIN assessments a ON a.id = g.assessment_id
                JOIN subjects sub ON sub.id = a.subject_id
                WHERE g.tenant_id = :tenant_id
                ORDER BY g.created_at DESC
                LIMIT 5
            """), {"tenant_id": tenant_id}).fetchall()

            recent_activities = [{
                "type": "grade",
                "description": f"{r.last_name} {r.first_name} — {r.assessment_name}: {r.score}/20",
                "time": r.created_at.isoformat() if r.created_at else None,
            } for r in grades]

        return {
            "department": dept,
            "stats": stats,
            "recent_activities": recent_activities,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error in department dashboard: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Classrooms ────────────────────────────────────────────────────

@router.get("/classrooms/")
def department_classrooms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """List classrooms linked to the current user's department."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        rows = db.execute(text("""
            SELECT c.id, c.name, c.level_id, c.capacity, c.section,
                   l.name AS level_name
            FROM classroom_departments cd
            JOIN classrooms c ON c.id = cd.class_id
            LEFT JOIN levels l ON l.id = c.level_id
            WHERE cd.department_id = :dept_id AND cd.tenant_id = :tenant_id
            ORDER BY c.name
        """), {"dept_id": dept["id"], "tenant_id": tenant_id}).fetchall()

        return [{
            "id": str(r.id), "name": r.name, "level_id": str(r.level_id) if r.level_id else None,
            "capacity": r.capacity, "section": r.section, "level_name": r.level_name,
        } for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error listing department classrooms: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Students ──────────────────────────────────────────────────────

@router.get("/students/")
def department_students(
    classroom_id: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """List students enrolled in the department's classrooms."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)
        if not class_ids:
            return {"students": [], "classrooms": []}

        # Classrooms list for filter dropdown
        cr_sql, cr_params = _any_in("id", "crids", class_ids)
        classrooms = db.execute(text(f"""
            SELECT id, name FROM classrooms
            WHERE {cr_sql} ORDER BY name
        """), cr_params).fetchall()

        cid_filter_sql, cid_filter_params = _any_in("e.class_id", "scids", class_ids)
        filters = f"AND {cid_filter_sql}"
        params: dict = {"tenant_id": tenant_id, **cid_filter_params}

        if classroom_id:
            filters = "AND e.class_id = :classroom_id"
            params["classroom_id"] = classroom_id

        search_filter = ""
        if search:
            search_filter = " AND (LOWER(s.first_name) LIKE LOWER(:search) OR LOWER(s.last_name) LIKE LOWER(:search) OR LOWER(s.registration_number) LIKE LOWER(:search))"
            params["search"] = f"%{search}%"

        rows = db.execute(text(f"""
            SELECT DISTINCT s.id, s.first_name, s.last_name, s.registration_number,
                   s.email, s.phone, s.photo_url,
                   c.id AS class_id, c.name AS class_name
            FROM enrollments e
            JOIN students s ON s.id = e.student_id
            JOIN classrooms c ON c.id = e.class_id
            WHERE e.tenant_id = :tenant_id AND e.status = 'active'
            {filters} {search_filter}
            ORDER BY s.last_name, s.first_name
        """), params).fetchall()

        return {
            "students": [{
                "id": str(r.id), "first_name": r.first_name, "last_name": r.last_name,
                "registration_number": r.registration_number, "email": r.email,
                "phone": r.phone, "photo_url": r.photo_url,
                "classroom": {"id": str(r.class_id), "name": r.class_name},
            } for r in rows],
            "classrooms": [{"id": str(c.id), "name": c.name} for c in classrooms],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error listing department students: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Teachers ──────────────────────────────────────────────────────

@router.get("/teachers/")
def department_teachers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """List teachers assigned to the department's classrooms with subjects & hours."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)
        if not class_ids:
            return {"teachers": [], "department": dept}

        class_filter_sql, class_filter_params = _any_in("ta.class_id", "cids", class_ids)
        if settings.is_sqlite:
            rows = db.execute(text(f"""
                SELECT DISTINCT
                    u.id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url,
                    (SELECT GROUP_CONCAT(DISTINCT sub2.name, ',') FROM subjects sub2
                     JOIN teacher_assignments ta2 ON ta2.subject_id = sub2.id
                     WHERE ta2.teacher_id = u.id AND ta2.tenant_id = :tenant_id) AS subjects,
                    (SELECT GROUP_CONCAT(DISTINCT c2.name, ',') FROM classrooms c2
                     WHERE c2.id IN (SELECT ta3.class_id FROM teacher_assignments ta3
                                     WHERE ta3.teacher_id = u.id AND ta3.tenant_id = :tenant_id)) AS classrooms,
                    COUNT(DISTINCT ta.id) AS assignment_count
                FROM teacher_assignments ta
                JOIN users u ON u.id = ta.teacher_id
                WHERE {class_filter_sql} AND ta.tenant_id = :tenant_id
                GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url
                ORDER BY u.last_name
            """), {**class_filter_params, "tenant_id": tenant_id}).fetchall()
        else:
            rows = db.execute(text(f"""
                SELECT DISTINCT
                    u.id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url,
                    array_agg(DISTINCT sub.name) FILTER (WHERE sub.name IS NOT NULL) AS subjects,
                    array_agg(DISTINCT c.name) FILTER (WHERE c.name IS NOT NULL) AS classrooms,
                    COUNT(DISTINCT ta.id) AS assignment_count
                FROM teacher_assignments ta
                JOIN users u ON u.id = ta.teacher_id
                LEFT JOIN subjects sub ON sub.id = ta.subject_id
                LEFT JOIN classrooms c ON c.id = ta.class_id
                WHERE {class_filter_sql} AND ta.tenant_id = :tenant_id
                GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url
                ORDER BY u.last_name
            """), {**class_filter_params, "tenant_id": tenant_id}).fetchall()

        # Hours for current month
        start_month = datetime.date.today().replace(day=1).isoformat()
        end_month = (datetime.date.today().replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

        hours_filter_sql, hours_filter_params = _any_in("class_id", "hcids", class_ids)
        hours_rows = db.execute(text(f"""
            SELECT teacher_id, SUM(hours_worked) AS total_hours
            FROM teacher_work_hours
            WHERE {hours_filter_sql} AND tenant_id = :tenant_id
            AND work_date BETWEEN :start AND :end
            GROUP BY teacher_id
        """), {**hours_filter_params, "tenant_id": tenant_id,
               "start": start_month, "end": end_month.isoformat()}).fetchall()

        hours_map = {str(h.teacher_id): float(h.total_hours or 0) for h in hours_rows}

        return {
            "department": dept,
            "teachers": [{
                "id": str(r.id), "first_name": r.first_name, "last_name": r.last_name,
                "email": r.email, "phone": r.phone, "avatar_url": r.avatar_url,
                "subjects": [x for x in (r.subjects.split(",") if isinstance(r.subjects, str) else (r.subjects or [])) if x],
                "classrooms_names": [x for x in (r.classrooms.split(",") if isinstance(r.classrooms, str) else (r.classrooms or [])) if x],
                "assignment_count": r.assignment_count,
                "hours_this_month": hours_map.get(str(r.id), 0.0),
            } for r in rows]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error listing department teachers: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Attendance ────────────────────────────────────────────────────

@router.get("/attendance/")
def department_attendance(
    period: str = Query("week", pattern="^(week|month)$"),
    classroom_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """Attendance records for the department's classrooms."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)
        if not class_ids:
            return {"records": [], "stats": {}, "classrooms": []}

        today = datetime.date.today()
        if period == "week":
            # Start of current week (Monday)
            start = today - datetime.timedelta(days=today.weekday())
            end = start + datetime.timedelta(days=6)
        else:
            start = today.replace(day=1)
            next_month = (today.replace(day=28) + datetime.timedelta(days=4))
            end = next_month.replace(day=1) - datetime.timedelta(days=1)

        cr_sql2, cr_params2 = _any_in("id", "atcrids", class_ids)
        classrooms = db.execute(text(f"""
            SELECT id, name FROM classrooms WHERE {cr_sql2} ORDER BY name
        """), cr_params2).fetchall()

        params: dict = {
            "tenant_id": tenant_id, "start": start.isoformat(), "end": end.isoformat()
        }

        if classroom_id:
            class_filter = "AND a.class_id = :classroom_id"
            params["classroom_id"] = classroom_id
        else:
            ac_sql, ac_params = _any_in("a.class_id", "atcids", class_ids)
            class_filter = f"AND {ac_sql}"
            params.update(ac_params)

        rows = db.execute(text(f"""
            SELECT a.id, a.date, a.status, a.notes,
                   s.id AS student_id, s.first_name, s.last_name, s.registration_number,
                   c.id AS class_id, c.name AS class_name
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            JOIN classrooms c ON c.id = a.class_id
            WHERE a.tenant_id = :tenant_id
            AND a.date BETWEEN :start AND :end
            {class_filter}
            ORDER BY a.date DESC, s.last_name
            LIMIT 500
        """), params).fetchall()

        records = [{
            "id": str(r.id), "date": r.date.isoformat() if r.date else None,
            "status": r.status, "notes": r.notes,
            "students": {"first_name": r.first_name, "last_name": r.last_name, "registration_number": r.registration_number},
            "classrooms": {"name": r.class_name},
        } for r in rows]

        total = len(records)
        present = sum(1 for r in records if r["status"] == "PRESENT")
        absent = sum(1 for r in records if r["status"] == "ABSENT")
        late = sum(1 for r in records if r["status"] == "LATE")
        excused = sum(1 for r in records if r["status"] == "EXCUSED")

        return {
            "department": dept,
            "classrooms": [{"id": str(c.id), "name": c.name} for c in classrooms],
            "records": records,
            "stats": {
                "total": total, "present": present, "absent": absent,
                "late": late, "excused": excused,
                "attendance_rate": round(((present + late) / total) * 100, 1) if total else 0,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error getting department attendance: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Exams ─────────────────────────────────────────────────────────

@router.get("/exams/")
def department_exams(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """List all exams for the department + subjects, terms, classrooms for the form."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)

        exams = db.execute(text("""
            SELECT e.id, e.name, e.description, e.exam_date, e.start_time, e.end_time,
                   e.room_name, e.max_score, e.status, e.class_id, e.subject_id, e.term_id,
                   e.department_id,
                   c.name AS classroom_name,
                   sub.name AS subject_name,
                   t.name AS term_name
            FROM exams e
            LEFT JOIN classrooms c ON c.id = e.class_id
            LEFT JOIN subjects sub ON sub.id = e.subject_id
            LEFT JOIN terms t ON t.id = e.term_id
            WHERE e.tenant_id = :tenant_id AND e.department_id = :dept_id
            ORDER BY e.exam_date ASC
        """), {"tenant_id": tenant_id, "dept_id": dept["id"]}).fetchall()

        cr_sql3, cr_params3 = _any_in("c.id", "excrids", class_ids)
        classrooms = db.execute(text(f"""
            SELECT c.id, c.name FROM classrooms c
            WHERE {cr_sql3} ORDER BY c.name
        """), cr_params3).fetchall() if class_ids else []

        subjects = db.execute(text("""
            SELECT id, name FROM subjects WHERE tenant_id = :tenant_id ORDER BY name
        """), {"tenant_id": tenant_id}).fetchall()

        terms = db.execute(text("""
            SELECT id, name FROM terms WHERE tenant_id = :tenant_id ORDER BY name
        """), {"tenant_id": tenant_id}).fetchall()

        return {
            "department": dept,
            "exams": [{
                "id": str(e.id), "name": e.name, "description": e.description,
                "exam_date": e.exam_date.isoformat() if e.exam_date else None,
                "start_time": str(e.start_time) if e.start_time else None,
                "end_time": str(e.end_time) if e.end_time else None,
                "room_name": e.room_name, "max_score": float(e.max_score or 20),
                "status": e.status,
                "class_id": str(e.class_id) if e.class_id else None,
                "subject_id": str(e.subject_id) if e.subject_id else None,
                "term_id": str(e.term_id) if e.term_id else None,
                "classroom": {"name": e.classroom_name} if e.classroom_name else None,
                "subject": {"name": e.subject_name} if e.subject_name else None,
                "term": {"name": e.term_name} if e.term_name else None,
            } for e in exams],
            "classrooms": [{"id": str(c.id), "name": c.name} for c in classrooms],
            "subjects": [{"id": str(s.id), "name": s.name} for s in subjects],
            "terms": [{"id": str(t.id), "name": t.name} for t in terms],
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error listing department exams: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@router.post("/exams/", status_code=status.HTTP_201_CREATED)
def create_exam(
    body: ExamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:write"))
):
    try:
        """Create an exam for the current user's department."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        exam_id = db.execute(text("""
            INSERT INTO exams (tenant_id, department_id, name, description, exam_date,
                               start_time, end_time, room_name, max_score, status,
                               class_id, subject_id, term_id, created_by, created_at)
            VALUES (:tenant_id, :dept_id, :name, :description, :exam_date,
                    :start_time, :end_time, :room_name, :max_score, :status,
                    :class_id, :subject_id, :term_id, :created_by, NOW())
            RETURNING id
        """), {
            "tenant_id": tenant_id, "dept_id": dept["id"],
            "name": body.name, "description": body.description,
            "exam_date": body.exam_date,
            "start_time": body.start_time, "end_time": body.end_time,
            "room_name": body.room_name, "max_score": body.max_score,
            "status": body.status,
            "class_id": body.class_id, "subject_id": body.subject_id,
            "term_id": body.term_id, "created_by": user_id,
        }).scalar()
        db.commit()
        return {"id": str(exam_id), "message": "Examen créé"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error creating exam: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@router.put("/exams/{exam_id}/")
def update_exam(
    exam_id: str,
    body: ExamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:write"))
):
    try:
        """Update an exam."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        result = db.execute(text("""
            UPDATE exams SET
                name = :name, description = :description, exam_date = :exam_date,
                start_time = :start_time, end_time = :end_time, room_name = :room_name,
                max_score = :max_score, status = :status,
                class_id = :class_id, subject_id = :subject_id, term_id = :term_id
            WHERE id = :exam_id AND tenant_id = :tenant_id AND department_id = :dept_id
        """), {
            "exam_id": exam_id, "tenant_id": tenant_id, "dept_id": dept["id"],
            "name": body.name, "description": body.description, "exam_date": body.exam_date,
            "start_time": body.start_time, "end_time": body.end_time,
            "room_name": body.room_name, "max_score": body.max_score,
            "status": body.status, "class_id": body.class_id,
            "subject_id": body.subject_id, "term_id": body.term_id,
        })
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Examen introuvable")
        return {"message": "Examen mis à jour"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error updating exam: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@router.delete("/exams/{exam_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:write"))
):
    try:
        """Delete an exam."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        result = db.execute(text("""
            DELETE FROM exams WHERE id = :exam_id AND tenant_id = :tenant_id AND department_id = :dept_id
        """), {"exam_id": exam_id, "tenant_id": tenant_id, "dept_id": dept["id"]})
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Examen introuvable")
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error deleting exam: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Schedule ──────────────────────────────────────────────────────

@router.get("/schedule/")
def department_schedule(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """Return schedule for all department classrooms."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)
        if not class_ids:
            return {"department": dept, "schedule": []}

        sc_sql, sc_params = _any_in("s.class_id", "schcids", class_ids)
        rows = db.execute(text(f"""
            SELECT s.id, s.day_of_week, s.start_time, s.end_time,
                   sub.name AS subject_name,
                   u.first_name AS teacher_first, u.last_name AS teacher_last,
                   c.name AS classroom_name
            FROM schedules s
            LEFT JOIN subjects sub ON sub.id = s.subject_id
            LEFT JOIN users u ON u.id = s.teacher_id
            LEFT JOIN classrooms c ON c.id = s.class_id
            WHERE {sc_sql} AND s.tenant_id = :tenant_id
            ORDER BY s.day_of_week, s.start_time
        """), {**sc_params, "tenant_id": tenant_id}).fetchall()

        return {
            "department": dept,
            "schedule": [{
                "id": str(r.id), "day_of_week": r.day_of_week,
                "start_time": str(r.start_time), "end_time": str(r.end_time),
                "subject": {"name": r.subject_name},
                "teacher": {"first_name": r.teacher_first, "last_name": r.teacher_last},
                "classroom": {"name": r.classroom_name},
            } for r in rows]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error getting department schedule: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


# ─── Department Reports ───────────────────────────────────────────────────────

@router.get("/reports/grades/")
def department_grades_report(
    term_id: str | None = None,
    classroom_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _perm: None = Depends(require_permission("departments:read"))
):
    try:
        """Grade summary report for the department."""
        tenant_id = current_user.get("tenant_id")
        user_id = current_user.get("id")
        if not tenant_id or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        dept = _get_user_department(db, user_id, tenant_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Aucun département assigné")

        class_ids = _get_department_classroom_ids(db, dept["id"], tenant_id)
        if not class_ids:
            return {"department": dept, "grades": []}

        gr_sql, gr_params = _any_in("e.class_id", "grcids", class_ids)
        params: dict = {"tenant_id": tenant_id, **gr_params}
        filters = f"AND {gr_sql}"

        if classroom_id:
            filters = "AND e.class_id = :classroom_id"
            params["classroom_id"] = classroom_id

        term_filter = ""
        if term_id:
            term_filter = "AND a.term_id = :term_id"
            params["term_id"] = term_id

        rows = db.execute(text(f"""
            SELECT s.id AS student_id, s.first_name, s.last_name, s.registration_number,
                   c.name AS classroom_name,
                   AVG(g.score) AS avg_score,
                   COUNT(g.id) AS grade_count,
                   MAX(g.score) AS max_score,
                   MIN(g.score) AS min_score
            FROM students s
            JOIN enrollments e ON e.student_id = s.id AND e.status = 'active'
            JOIN classrooms c ON c.id = e.class_id
            LEFT JOIN grades g ON g.student_id = s.id AND g.tenant_id = :tenant_id
            LEFT JOIN assessments a ON a.id = g.assessment_id {term_filter}
            WHERE e.tenant_id = :tenant_id {filters}
            GROUP BY s.id, s.first_name, s.last_name, s.registration_number, c.name
            ORDER BY CASE WHEN avg_score IS NULL THEN 1 ELSE 0 END, avg_score DESC
        """), params).fetchall()

        return {
            "department": dept,
            "grades": [{
                "student_id": str(r.student_id),
                "first_name": r.first_name, "last_name": r.last_name,
                "registration_number": r.registration_number,
                "classroom_name": r.classroom_name,
                "avg_score": round(float(r.avg_score), 2) if r.avg_score else None,
                "grade_count": r.grade_count or 0,
                "max_score": float(r.max_score) if r.max_score else None,
                "min_score": float(r.min_score) if r.min_score else None,
            } for r in rows]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error getting department grades report: %s", e)
        logger.error("Operation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")
