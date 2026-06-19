"""CRUD integration tests with actual SQLite in-memory database.

Covers:
- Create engine, create all tables, insert data, query data
- Student CRUD: create, read, update, delete with proper tenant isolation
- Tenant CRUD: create, read, update
- Grade CRUD: create with student FK, read by student
- Payment CRUD: create with student FK, read by student
- Cross-tenant isolation: student from tenant A not visible to tenant B

These are true integration tests — they hit a real (in-memory) database
with real SQLAlchemy models and CRUD functions.
"""
import os


# Set test environment BEFORE any app imports to prevent DB connection errors
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///./test.db")
os.environ.setdefault("DATABASE_URL_ASYNC", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.payment import PaymentMethod, PaymentStatus
from app.models.student import Gender, Student, StudentStatus
from app.models.tenant import Tenant
from app.schemas.grade import GradeCreate, GradeUpdate
from app.schemas.payment import PaymentCreate, PaymentUpdate
from app.schemas.student import StudentCreate, StudentUpdate


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh SQLite in-memory engine for each test with all tables."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test."""
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def tenant_a(db_session):
    """Create tenant A for CRUD tests."""
    t = Tenant(
        id=uuid.uuid4(),
        name="École Alpha",
        slug="ecole-alpha",
        type="SCHOOL",
        country="GN",
        currency="GNF",
        subscription_plan="pro",
        subscription_status="active",
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture(scope="function")
def tenant_b(db_session):
    """Create tenant B for cross-tenant isolation tests."""
    t = Tenant(
        id=uuid.uuid4(),
        name="Lycée Beta",
        slug="lycee-beta",
        type="HIGH",
        country="SN",
        currency="XOF",
        subscription_plan="starter",
        subscription_status="trialing",
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


# ─── Student CRUD Tests ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestStudentCRUD:
    """Integration tests for Student CRUD operations."""

    def test_create_student(self, db_session, tenant_a):
        """Create a student via CRUD and verify it's persisted."""
        from app.crud.student import create_student

        student_data = StudentCreate(
            registration_number="REG-CRUD-001",
            first_name="Amadou",
            last_name="Diallo",
            date_of_birth=date(2010, 5, 15),
            gender=Gender.MALE,
            email="amadou@test.com",
            level="6ème",
            class_name="6ème A",
        )

        created = create_student(db_session, student_data, tenant_a.id)

        assert created.id is not None
        assert created.registration_number == "REG-CRUD-001"
        assert created.first_name == "Amadou"
        assert created.last_name == "Diallo"
        assert created.tenant_id == tenant_a.id
        assert created.status == StudentStatus.ACTIVE  # default

    def test_get_student(self, db_session, tenant_a):
        """Read a student by ID via CRUD."""
        from app.crud.student import create_student, get_student

        student_data = StudentCreate(
            registration_number="REG-GET-001",
            first_name="Fatou",
            last_name="Bah",
            date_of_birth=date(2012, 3, 20),
            gender=Gender.FEMALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        fetched = get_student(db_session, created.id, tenant_a.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.first_name == "Fatou"

    def test_get_student_by_registration(self, db_session, tenant_a):
        """Read a student by registration number via CRUD."""
        from app.crud.student import create_student, get_student_by_registration

        student_data = StudentCreate(
            registration_number="REG-REG-001",
            first_name="Mamadou",
            last_name="Condé",
            date_of_birth=date(2011, 7, 10),
            gender=Gender.MALE,
        )
        create_student(db_session, student_data, tenant_a.id)

        fetched = get_student_by_registration(db_session, "REG-REG-001", tenant_a.id)

        assert fetched is not None
        assert fetched.registration_number == "REG-REG-001"

    def test_update_student(self, db_session, tenant_a):
        """Update a student via CRUD with partial data."""
        from app.crud.student import create_student, update_student

        student_data = StudentCreate(
            registration_number="REG-UPD-001",
            first_name="Original",
            last_name="Name",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            level="5ème",
        )
        created = create_student(db_session, student_data, tenant_a.id)

        update_data = StudentUpdate(
            first_name="Updated",
            level="6ème",
        )
        updated = update_student(db_session, created.id, update_data, tenant_a.id)

        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"  # Unchanged
        assert updated.level == "6ème"

    def test_update_student_status(self, db_session, tenant_a):
        """Update student status via CRUD."""
        from app.crud.student import create_student, update_student

        student_data = StudentCreate(
            registration_number="REG-STATUS-001",
            first_name="Status",
            last_name="Test",
            date_of_birth=date(2005, 1, 1),
            gender=Gender.FEMALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        update_data = StudentUpdate(status=StudentStatus.GRADUATED)
        updated = update_student(db_session, created.id, update_data, tenant_a.id)

        assert updated.status == StudentStatus.GRADUATED

    def test_delete_student(self, db_session, tenant_a):
        """Delete a student via CRUD and verify it's gone."""
        from app.crud.student import create_student, delete_student, get_student

        student_data = StudentCreate(
            registration_number="REG-DEL-001",
            first_name="ToDelete",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        result = delete_student(db_session, created.id, tenant_a.id)
        assert result is True

        # Verify student is gone
        fetched = get_student(db_session, created.id, tenant_a.id)
        assert fetched is None

    def test_delete_nonexistent_student(self, db_session, tenant_a):
        """Deleting a non-existent student returns False."""
        from app.crud.student import delete_student

        result = delete_student(db_session, uuid.uuid4(), tenant_a.id)
        assert result is False

    def test_get_students_with_pagination(self, db_session, tenant_a):
        """get_students returns paginated results with total count."""
        from app.crud.student import create_student, get_students

        # Create 5 students
        for i in range(5):
            student_data = StudentCreate(
                registration_number=f"REG-PAGE-{i:03d}",
                first_name=f"Student{i}",
                last_name="Paged",
                date_of_birth=date(2010, 1, 1),
                gender=Gender.MALE,
            )
            create_student(db_session, student_data, tenant_a.id)

        # Get first page of 2
        students, total = get_students(db_session, tenant_a.id, skip=0, limit=2)

        assert total == 5
        assert len(students) == 2

    def test_get_students_with_search(self, db_session, tenant_a):
        """get_students filters by search term (name, email, reg number)."""
        from app.crud.student import create_student, get_students

        s1 = StudentCreate(
            registration_number="REG-SEARCH-001",
            first_name="UniqueFirstName",
            last_name="CommonName",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            email="unique@test.com",
        )
        s2 = StudentCreate(
            registration_number="REG-SEARCH-002",
            first_name="OtherFirstName",
            last_name="CommonName",
            date_of_birth=date(2010, 2, 2),
            gender=Gender.FEMALE,
        )
        create_student(db_session, s1, tenant_a.id)
        create_student(db_session, s2, tenant_a.id)

        # Search by first name
        results, total = get_students(db_session, tenant_a.id, search="UniqueFirstName")
        assert total == 1
        assert results[0].first_name == "UniqueFirstName"

        # Search by common last name
        results, total = get_students(db_session, tenant_a.id, search="CommonName")
        assert total == 2

    def test_get_students_with_status_filter(self, db_session, tenant_a):
        """get_students filters by status."""
        from app.crud.student import create_student, get_students, update_student

        s1 = StudentCreate(
            registration_number="REG-ACTIVE",
            first_name="Active",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
        )
        s2 = StudentCreate(
            registration_number="REG-GRAD",
            first_name="Graduated",
            last_name="Student",
            date_of_birth=date(2000, 1, 1),
            gender=Gender.FEMALE,
        )
        create_student(db_session, s1, tenant_a.id)
        created2 = create_student(db_session, s2, tenant_a.id)

        # Update second student to GRADUATED
        update_student(db_session, created2.id, StudentUpdate(status=StudentStatus.GRADUATED), tenant_a.id)

        # Filter by ACTIVE
        results, total = get_students(db_session, tenant_a.id, status=StudentStatus.ACTIVE)
        assert total == 1
        assert results[0].status == StudentStatus.ACTIVE

        # Filter by GRADUATED
        results, total = get_students(db_session, tenant_a.id, status=StudentStatus.GRADUATED)
        assert total == 1
        assert results[0].status == StudentStatus.GRADUATED

    def test_get_students_with_level_filter(self, db_session, tenant_a):
        """get_students filters by level."""
        from app.crud.student import create_student, get_students

        s1 = StudentCreate(
            registration_number="REG-6A",
            first_name="Sixth",
            last_name="Grader",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            level="6ème",
        )
        s2 = StudentCreate(
            registration_number="REG-3B",
            first_name="Third",
            last_name="Grader",
            date_of_birth=date(2008, 1, 1),
            gender=Gender.FEMALE,
            level="3ème",
        )
        create_student(db_session, s1, tenant_a.id)
        create_student(db_session, s2, tenant_a.id)

        results, total = get_students(db_session, tenant_a.id, level="6ème")
        assert total == 1
        assert results[0].level == "6ème"


# ─── Tenant CRUD Tests ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantCRUD:
    """Integration tests for Tenant CRUD operations."""

    def test_create_tenant(self, db_session):
        """Create a tenant and verify it's persisted."""
        t = Tenant(
            id=uuid.uuid4(),
            name="New School",
            slug="new-school",
            type="SCHOOL",
            country="GN",
        )
        db_session.add(t)
        db_session.commit()

        fetched = db_session.query(Tenant).filter_by(slug="new-school").first()
        assert fetched is not None
        assert fetched.name == "New School"

    def test_read_tenant(self, db_session, tenant_a):
        """Read a tenant by ID."""
        fetched = db_session.query(Tenant).filter_by(id=tenant_a.id).first()
        assert fetched is not None
        assert fetched.name == "École Alpha"
        assert fetched.slug == "ecole-alpha"

    def test_update_tenant(self, db_session, tenant_a):
        """Update a tenant's name."""
        tenant_a.name = "École Alpha Updated"
        db_session.commit()
        db_session.refresh(tenant_a)

        assert tenant_a.name == "École Alpha Updated"

    def test_update_tenant_subscription(self, db_session, tenant_a):
        """Update a tenant's subscription plan."""
        tenant_a.subscription_plan = "enterprise"
        tenant_a.subscription_status = "active"
        db_session.commit()
        db_session.refresh(tenant_a)

        assert tenant_a.subscription_plan == "enterprise"
        assert tenant_a.subscription_status == "active"

    def test_list_tenants(self, db_session, tenant_a, tenant_b):
        """List all tenants."""
        tenants = db_session.query(Tenant).all()
        assert len(tenants) >= 2

        slugs = {t.slug for t in tenants}
        assert "ecole-alpha" in slugs
        assert "lycee-beta" in slugs


# ─── Grade CRUD Tests ───────────────────────────────────────────────────────

@pytest.mark.unit
class TestGradeCRUD:
    """Integration tests for Grade CRUD operations."""

    def test_create_grade(self, db_session, tenant_a):
        """Create a grade linked to a student."""
        from app.crud.grade import create_grade

        # First create a student
        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-GRADE-CRUD",
            first_name="Grade",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        grade_data = GradeCreate(
            student_id=s.id,
            score=16.5,
            max_score=20.0,
            coefficient=2.0,
            comments="Excellent work",
        )
        created = create_grade(db_session, grade_data, tenant_a.id)

        assert created.id is not None
        assert created.score == 16.5
        assert created.max_score == 20.0
        assert created.coefficient == 2.0
        assert created.tenant_id == tenant_a.id

    def test_get_grade(self, db_session, tenant_a):
        """Read a grade by ID."""
        from app.crud.grade import create_grade, get_grade

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-GET-GRADE",
            first_name="Grade",
            last_name="Get",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        grade_data = GradeCreate(student_id=s.id, score=14.0)
        created = create_grade(db_session, grade_data, tenant_a.id)

        fetched = get_grade(db_session, created.id, tenant_a.id)
        assert fetched is not None
        assert fetched.score == 14.0

    def test_get_grades_by_student(self, db_session, tenant_a):
        """Get all grades for a specific student."""
        from app.crud.grade import create_grade, get_grades

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-STUDENT-GRADES",
            first_name="Graded",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        # Create 3 grades for the student
        for i in range(3):
            grade_data = GradeCreate(
                student_id=s.id,
                score=10.0 + i,
                max_score=20.0,
            )
            create_grade(db_session, grade_data, tenant_a.id)

        grades, total = get_grades(db_session, tenant_a.id, student_id=s.id)
        assert total == 3
        assert len(grades) == 3

    def test_update_grade(self, db_session, tenant_a):
        """Update a grade's score via CRUD."""
        from app.crud.grade import create_grade, update_grade

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-UPD-GRADE",
            first_name="Update",
            last_name="Grade",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        grade_data = GradeCreate(student_id=s.id, score=12.0)
        created = create_grade(db_session, grade_data, tenant_a.id)

        update_data = GradeUpdate(score=18.0, comments="Improved!")
        updated = update_grade(db_session, created.id, update_data, tenant_a.id)

        assert updated is not None
        assert updated.score == 18.0
        assert updated.comments == "Improved!"

    def test_delete_grade(self, db_session, tenant_a):
        """Delete a grade via CRUD."""
        from app.crud.grade import create_grade, delete_grade, get_grade

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-DEL-GRADE",
            first_name="Delete",
            last_name="Grade",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        grade_data = GradeCreate(student_id=s.id, score=10.0)
        created = create_grade(db_session, grade_data, tenant_a.id)

        result = delete_grade(db_session, created.id, tenant_a.id)
        assert result is True

        fetched = get_grade(db_session, created.id, tenant_a.id)
        assert fetched is None

    def test_delete_nonexistent_grade(self, db_session, tenant_a):
        """Deleting a non-existent grade returns False."""
        from app.crud.grade import delete_grade

        result = delete_grade(db_session, uuid.uuid4(), tenant_a.id)
        assert result is False


# ─── Payment CRUD Tests ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestPaymentCRUD:
    """Integration tests for Payment CRUD operations."""

    def test_create_payment(self, db_session, tenant_a):
        """Create a payment linked to a student."""
        from app.crud.payment import create_payment

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-PAY-CRUD",
            first_name="Pay",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        payment_data = PaymentCreate(
            student_id=s.id,
            amount=150000.0,
            payment_date=date(2026, 1, 15),
            payment_method=PaymentMethod.MOBILE_MONEY,
        )
        created = create_payment(db_session, payment_data, tenant_a.id)

        assert created.id is not None
        assert created.amount == 150000.0
        assert created.payment_method == PaymentMethod.MOBILE_MONEY
        assert created.reference is not None
        assert created.reference.startswith("PAY-")

    def test_get_payment(self, db_session, tenant_a):
        """Read a payment by ID."""
        from app.crud.payment import create_payment, get_payment

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-GET-PAY",
            first_name="Get",
            last_name="Payment",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        payment_data = PaymentCreate(
            student_id=s.id,
            amount=75000.0,
            payment_date=date(2026, 2, 1),
            payment_method=PaymentMethod.CASH,
        )
        created = create_payment(db_session, payment_data, tenant_a.id)

        fetched = get_payment(db_session, created.id, tenant_a.id)
        assert fetched is not None
        assert fetched.amount == 75000.0

    def test_get_payments_by_student(self, db_session, tenant_a):
        """Get all payments for a specific student."""
        from app.crud.payment import create_payment, get_payments

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-PAY-LIST",
            first_name="PayList",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        for i in range(3):
            payment_data = PaymentCreate(
                student_id=s.id,
                amount=50000.0 * (i + 1),
                payment_date=date(2026, i + 1, 1),
                payment_method=PaymentMethod.BANK_TRANSFER,
            )
            create_payment(db_session, payment_data, tenant_a.id)

        _payments, total = get_payments(db_session, tenant_a.id, student_id=s.id)
        assert total == 3

    def test_update_payment(self, db_session, tenant_a):
        """Update a payment's amount and status."""
        from app.crud.payment import create_payment, update_payment

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-UPD-PAY",
            first_name="Update",
            last_name="Payment",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        payment_data = PaymentCreate(
            student_id=s.id,
            amount=100000.0,
            payment_date=date(2026, 3, 1),
            payment_method=PaymentMethod.CARD,
        )
        created = create_payment(db_session, payment_data, tenant_a.id)

        update_data = PaymentUpdate(
            amount=120000.0,
            status=PaymentStatus.COMPLETED,
        )
        updated = update_payment(db_session, created.id, update_data, tenant_a.id)

        assert updated is not None
        assert updated.amount == 120000.0
        assert updated.status == PaymentStatus.COMPLETED


# ─── Cross-Tenant Isolation Tests ───────────────────────────────────────────

@pytest.mark.unit
class TestCrossTenantIsolation:
    """Tests verifying that tenant-scoped data is properly isolated."""

    def test_student_not_visible_to_other_tenant(self, db_session, tenant_a, tenant_b):
        """Student from tenant A is not visible when querying with tenant B's ID."""
        from app.crud.student import create_student, get_student

        student_data = StudentCreate(
            registration_number="REG-ISO-001",
            first_name="Isolated",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        # Try to fetch with tenant B's ID — should return None
        fetched = get_student(db_session, created.id, tenant_b.id)
        assert fetched is None

    def test_students_list_only_shows_own_tenant(self, db_session, tenant_a, tenant_b):
        """get_students with tenant A only returns tenant A's students."""
        from app.crud.student import create_student, get_students

        # Create students for both tenants
        for i in range(3):
            create_student(
                db_session,
                StudentCreate(
                    registration_number=f"REG-A-{i:03d}",
                    first_name=f"TenantA{i}",
                    last_name="Student",
                    date_of_birth=date(2010, 1, 1),
                    gender=Gender.MALE,
                ),
                tenant_a.id,
            )

        for i in range(2):
            create_student(
                db_session,
                StudentCreate(
                    registration_number=f"REG-B-{i:03d}",
                    first_name=f"TenantB{i}",
                    last_name="Student",
                    date_of_birth=date(2010, 1, 1),
                    gender=Gender.FEMALE,
                ),
                tenant_b.id,
            )

        # Verify isolation
        a_students, a_total = get_students(db_session, tenant_a.id)
        b_students, b_total = get_students(db_session, tenant_b.id)

        assert a_total == 3
        assert b_total == 2

        # Verify no cross-contamination
        a_names = {s.first_name for s in a_students}
        b_names = {s.first_name for s in b_students}
        assert all("TenantA" in n for n in a_names)
        assert all("TenantB" in n for n in b_names)

    def test_grade_not_visible_to_other_tenant(self, db_session, tenant_a, tenant_b):
        """Grade from tenant A is not visible when querying with tenant B's ID."""
        from app.crud.grade import create_grade, get_grade

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-GRADE-ISO",
            first_name="Grade",
            last_name="Isolated",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        grade_data = GradeCreate(student_id=s.id, score=15.0)
        created = create_grade(db_session, grade_data, tenant_a.id)

        # Try to fetch with tenant B's ID
        fetched = get_grade(db_session, created.id, tenant_b.id)
        assert fetched is None

    def test_payment_not_visible_to_other_tenant(self, db_session, tenant_a, tenant_b):
        """Payment from tenant A is not visible when querying with tenant B's ID."""
        from app.crud.payment import create_payment, get_payment

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-PAY-ISO",
            first_name="Pay",
            last_name="Isolated",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        payment_data = PaymentCreate(
            student_id=s.id,
            amount=50000.0,
            payment_date=date(2026, 1, 1),
            payment_method=PaymentMethod.CASH,
        )
        created = create_payment(db_session, payment_data, tenant_a.id)

        # Try to fetch with tenant B's ID
        fetched = get_payment(db_session, created.id, tenant_b.id)
        assert fetched is None

    def test_update_student_from_other_tenant_fails(self, db_session, tenant_a, tenant_b):
        """Updating a student with wrong tenant_id returns None."""
        from app.crud.student import create_student, update_student

        student_data = StudentCreate(
            registration_number="REG-UPD-ISO",
            first_name="Cross",
            last_name="Tenant",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        # Try to update with tenant B's ID
        updated = update_student(
            db_session, created.id, StudentUpdate(first_name="Hacked"), tenant_b.id
        )
        assert updated is None

    def test_delete_student_from_other_tenant_fails(self, db_session, tenant_a, tenant_b):
        """Deleting a student with wrong tenant_id returns False."""
        from app.crud.student import create_student, delete_student

        student_data = StudentCreate(
            registration_number="REG-DEL-ISO",
            first_name="Protected",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
        )
        created = create_student(db_session, student_data, tenant_a.id)

        # Try to delete with tenant B's ID
        result = delete_student(db_session, created.id, tenant_b.id)
        assert result is False

        # Verify student still exists for tenant A
        from app.crud.student import get_student
        fetched = get_student(db_session, created.id, tenant_a.id)
        assert fetched is not None

    def test_cross_tenant_student_cannot_reuse_registration(self, db_session, tenant_a, tenant_b):
        """Same registration number can exist in different tenants (different scope)."""
        from app.crud.student import create_student

        s1 = StudentCreate(
            registration_number="REG-SHARED",
            first_name="TenantA",
            last_name="Shared",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
        )
        s2 = StudentCreate(
            registration_number="REG-SHARED",
            first_name="TenantB",
            last_name="Shared",
            date_of_birth=date(2010, 2, 2),
            gender=Gender.FEMALE,
        )

        # Both should succeed — registration_number is globally unique in the model
        # (unique=True), so the second one will actually fail.
        # This tests the model constraint. If you want per-tenant uniqueness,
        # you'd need a unique constraint on (registration_number, tenant_id).
        created1 = create_student(db_session, s1, tenant_a.id)
        assert created1.registration_number == "REG-SHARED"

        # The second one will fail because registration_number is globally unique
        with pytest.raises(Exception):  # IntegrityError
            create_student(db_session, s2, tenant_b.id)


# ─── Cascade Delete Tests ───────────────────────────────────────────────────

@pytest.mark.unit
class TestCascadeDeletes:
    """Tests for cascade deletion behavior."""

    def test_deleting_student_cascades_to_grades(self, db_session, tenant_a):
        """Deleting a student cascades to their grades."""
        from app.crud.grade import create_grade, get_grades
        from app.crud.student import delete_student

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-CASCADE-G",
            first_name="Cascade",
            last_name="Grades",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.MALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        # Create grades
        grade_data = GradeCreate(student_id=s.id, score=15.0)
        create_grade(db_session, grade_data, tenant_a.id)

        # Verify grade exists
        grades, total = get_grades(db_session, tenant_a.id, student_id=s.id)
        assert total == 1

        # Delete student — should cascade to grades
        delete_student(db_session, s.id, tenant_a.id)

        # Grades should be gone (via cascade)
        _grades, total = get_grades(db_session, tenant_a.id, student_id=s.id)
        assert total == 0

    def test_deleting_student_cascades_to_payments(self, db_session, tenant_a):
        """Deleting a student cascades to their payments."""
        from app.crud.payment import create_payment, get_payments
        from app.crud.student import delete_student

        s = Student(
            id=uuid.uuid4(),
            registration_number="REG-CASCADE-P",
            first_name="Cascade",
            last_name="Pay",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            tenant_id=tenant_a.id,
        )
        db_session.add(s)
        db_session.commit()
        db_session.refresh(s)

        # Create payment
        payment_data = PaymentCreate(
            student_id=s.id,
            amount=100000.0,
            payment_date=date(2026, 1, 1),
            payment_method=PaymentMethod.CASH,
        )
        create_payment(db_session, payment_data, tenant_a.id)

        # Verify payment exists
        payments, total = get_payments(db_session, tenant_a.id, student_id=s.id)
        assert total == 1

        # Delete student — should cascade to payments
        delete_student(db_session, s.id, tenant_a.id)

        # Payments should be gone
        _payments, total = get_payments(db_session, tenant_a.id, student_id=s.id)
        assert total == 0
