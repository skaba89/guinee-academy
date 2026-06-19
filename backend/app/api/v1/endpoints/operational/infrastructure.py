import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.crud import academic as crud
from app.models.associations import class_subjects, classroom_departments, subject_levels


logger = logging.getLogger(__name__)

from app.schemas.academic import (
    Classroom,
    ClassroomCreate,
    Enrollment,
    EnrollmentCreate,
    Program,
    ProgramCreate,
    Room,
    RoomCreate,
)


router = APIRouter()

# --- Rooms ---
@router.get("/rooms/", response_model=list[Room])
def read_rooms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:read")),
):
    """List rooms. Requires rooms:read permission."""
    return crud.get_rooms(db, tenant_id=current_user.get("tenant_id"))

@router.post("/rooms/", response_model=Room)
def create_room(
    obj_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:write")),
):
    """Create a room. Requires rooms:write permission."""
    return crud.create_room(db, obj_in=obj_in, tenant_id=current_user.get("tenant_id"))

# --- Programs ---
@router.get("/programs/", response_model=list[Program])
def read_programs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:read")),
):
    """List programs. Requires rooms:read permission."""
    return crud.get_programs(db, tenant_id=current_user.get("tenant_id"))

@router.post("/programs/", response_model=Program)
def create_program(
    obj_in: ProgramCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:write")),
):
    """Create a program. Requires rooms:write permission."""
    return crud.create_program(db, obj_in=obj_in, tenant_id=current_user.get("tenant_id"))

# --- Classrooms (Classes) ---
@router.get("/classrooms/", response_model=list[Classroom])
def read_classrooms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:read")),
):
    """List classrooms. Requires rooms:read permission."""
    return crud.get_classrooms(db, tenant_id=current_user.get("tenant_id"))

@router.post("/classrooms/", response_model=Classroom)
def create_classroom(
    obj_in: ClassroomCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:write")),
):
    """Create a classroom. Requires rooms:write permission."""
    return crud.create_classroom(db, obj_in=obj_in, tenant_id=current_user.get("tenant_id"))

# --- Enrollments ---
@router.get("/enrollments/", response_model=list[Enrollment])
def read_enrollments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("students:read")),
):
    """List enrollments. Requires students:read permission."""
    return crud.get_enrollments(db, tenant_id=current_user.get("tenant_id"))

@router.post("/enrollments/", response_model=Enrollment)
def create_enrollment(
    obj_in: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("students:write")),
):
    """Create an enrollment. Requires students:write permission."""
    return crud.create_enrollment(db, obj_in=obj_in, tenant_id=current_user.get("tenant_id"))

# --- Associations Helpers ---

@router.get("/all-subject-levels/")
def read_all_subject_levels(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("subjects:read")),
):
    """List subject-level associations. Requires subjects:read permission."""
    tenant_id = current_user.get("tenant_id")
    rows = db.execute(subject_levels.select().where(subject_levels.c.tenant_id == tenant_id)).fetchall()
    return [{"subject_id": str(r.subject_id), "level_id": str(r.level_id)} for r in rows]

@router.get("/classroom-departments/")
def read_classroom_departments_list(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("departments:read")),
):
    """List classroom-department associations. Requires departments:read permission."""
    tenant_id = current_user.get("tenant_id")
    rows = db.execute(classroom_departments.select().where(classroom_departments.c.tenant_id == tenant_id)).fetchall()
    return [{"class_id": str(r.class_id), "department_id": str(r.department_id)} for r in rows]

@router.get("/classrooms/{class_id}/subjects/")
def read_classroom_subjects(
    class_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("subjects:read")),
):
    """List subjects for a classroom. Requires subjects:read permission."""
    tenant_id = current_user.get("tenant_id")
    rows = db.execute(class_subjects.select().where(
        (class_subjects.c.class_id == class_id) & (class_subjects.c.tenant_id == tenant_id)
    )).fetchall()
    return [str(r.subject_id) for r in rows]

@router.get("/classrooms/{class_id}/departments/")
def read_classroom_departments(
    class_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("departments:read")),
):
    """List departments for a classroom. Requires departments:read permission."""
    tenant_id = current_user.get("tenant_id")
    rows = db.execute(classroom_departments.select().where(
        (classroom_departments.c.class_id == class_id) & (classroom_departments.c.tenant_id == tenant_id)
    )).fetchall()
    return [str(r.department_id) for r in rows]

@router.get("/rooms/count/")
def count_rooms(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("rooms:read")),
):
    """Count rooms. Requires rooms:read permission."""
    tenant_id = current_user.get("tenant_id")
    return db.execute(text("SELECT COUNT(*) FROM rooms WHERE tenant_id = :tenant_id"), {"tenant_id": tenant_id}).scalar() or 0

@router.get("/enrollments/counts/")
def read_enrollment_counts(
    class_ids: list[UUID] = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("students:read")),
):
    """Count enrollments per class. Requires students:read permission."""
    tenant_id = current_user.get("tenant_id")
    if not class_ids:
        return {}
    rows = db.execute(text("""
        SELECT class_id, COUNT(*) as count
        FROM enrollments
        WHERE tenant_id = :tenant_id AND class_id = ANY(:class_ids) AND status = 'active'
        GROUP BY class_id
    """), {"tenant_id": tenant_id, "class_ids": class_ids}).fetchall()
    return {str(r.class_id): r.count for r in rows}

@router.post("/classrooms/{class_id}/subjects/{subject_id}/")
def assign_subject_to_classroom(
    class_id: UUID,
    subject_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("subjects:write")),
):
    """Assign a subject to a classroom. Requires subjects:write permission."""
    tenant_id = current_user.get("tenant_id")
    db.execute(class_subjects.insert().values(
        tenant_id=tenant_id,
        class_id=class_id,
        subject_id=subject_id,
        is_optional=payload.get("is_optional", False),
        coefficient=payload.get("coefficient", 1.0)
    ))
    db.commit()
    return {"status": "success"}

@router.delete("/classrooms/{class_id}/subjects/{subject_id}/")
def remove_subject_from_classroom(
    class_id: UUID,
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("subjects:write")),
):
    """Remove a subject from a classroom. Requires subjects:write permission."""
    tenant_id = current_user.get("tenant_id")
    db.execute(class_subjects.delete().where(
        (class_subjects.c.class_id == class_id) &
        (class_subjects.c.subject_id == subject_id) &
        (class_subjects.c.tenant_id == tenant_id)
    ))
    db.commit()
    return {"status": "success"}
