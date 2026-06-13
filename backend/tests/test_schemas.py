"""Comprehensive tests for Pydantic schema validation.

Covers:
- StudentCreate: required fields, min_length validation, email validation
- StudentUpdate: all optional, partial updates
- PaymentCreate: required fields, amount positive validation
- GradeCreate: score range validation
- TenantCreate: required fields, slug format

These are pure unit tests — no database or HTTP client needed.
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
from pydantic import ValidationError


# ─── StudentCreate Tests ────────────────────────────────────────────────────

@pytest.mark.unit
class TestStudentCreateSchema:
    """Tests for the StudentCreate Pydantic schema."""

    def test_valid_student_create(self):
        """StudentCreate accepts all required fields with valid data."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        data = StudentCreate(
            registration_number="REG-001",
            first_name="Amadou",
            last_name="Diallo",
            date_of_birth=date(2010, 5, 15),
            gender=Gender.MALE,
            email="amadou@test.com",
        )
        assert data.registration_number == "REG-001"
        assert data.first_name == "Amadou"
        assert data.gender == Gender.MALE

    def test_student_create_requires_registration_number(self):
        """StudentCreate fails without registration_number."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "registration_number" in field_names

    def test_student_create_requires_first_name(self):
        """StudentCreate fails without first_name."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "first_name" in field_names

    def test_student_create_requires_last_name(self):
        """StudentCreate fails without last_name."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "last_name" in field_names

    def test_student_create_requires_date_of_birth(self):
        """StudentCreate fails without date_of_birth."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                last_name="Diallo",
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "date_of_birth" in field_names

    def test_student_create_requires_gender(self):
        """StudentCreate fails without gender."""
        from app.schemas.student import StudentCreate

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "gender" in field_names

    def test_student_create_first_name_min_length(self):
        """StudentCreate rejects empty first_name (min_length=1)."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        first_name_errors = [e for e in errors if e["loc"][-1] == "first_name"]
        assert len(first_name_errors) > 0

    def test_student_create_last_name_min_length(self):
        """StudentCreate rejects empty last_name (min_length=1)."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                last_name="",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        last_name_errors = [e for e in errors if e["loc"][-1] == "last_name"]
        assert len(last_name_errors) > 0

    def test_student_create_registration_number_min_length(self):
        """StudentCreate rejects empty registration_number (min_length=1)."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="",
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        reg_errors = [e for e in errors if e["loc"][-1] == "registration_number"]
        assert len(reg_errors) > 0

    def test_student_create_valid_email(self):
        """StudentCreate accepts valid email addresses."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        data = StudentCreate(
            registration_number="REG-001",
            first_name="Amadou",
            last_name="Diallo",
            date_of_birth=date(2010, 5, 15),
            gender=Gender.MALE,
            email="amadou.diallo@test.com",
        )
        assert data.email == "amadou.diallo@test.com"

    def test_student_create_invalid_email(self):
        """StudentCreate rejects invalid email addresses."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
                email="not-an-email",
            )
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if e["loc"][-1] == "email"]
        assert len(email_errors) > 0

    def test_student_create_email_optional(self):
        """StudentCreate allows email to be omitted."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        data = StudentCreate(
            registration_number="REG-001",
            first_name="Amadou",
            last_name="Diallo",
            date_of_birth=date(2010, 5, 15),
            gender=Gender.MALE,
        )
        assert data.email is None

    def test_student_create_parent_email_validation(self):
        """StudentCreate validates parent_email as proper email."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
                parent_email="bad-email",
            )
        errors = exc_info.value.errors()
        parent_email_errors = [e for e in errors if e["loc"][-1] == "parent_email"]
        assert len(parent_email_errors) > 0

    def test_student_create_max_length_first_name(self):
        """StudentCreate rejects first_name longer than 100 characters."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="REG-001",
                first_name="A" * 101,
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        fn_errors = [e for e in errors if e["loc"][-1] == "first_name"]
        assert len(fn_errors) > 0

    def test_student_create_max_length_registration_number(self):
        """StudentCreate rejects registration_number longer than 50 characters."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        with pytest.raises(ValidationError) as exc_info:
            StudentCreate(
                registration_number="R" * 51,
                first_name="Amadou",
                last_name="Diallo",
                date_of_birth=date(2010, 5, 15),
                gender=Gender.MALE,
            )
        errors = exc_info.value.errors()
        reg_errors = [e for e in errors if e["loc"][-1] == "registration_number"]
        assert len(reg_errors) > 0

    def test_student_create_all_optional_fields(self):
        """StudentCreate accepts all optional fields at once."""
        from app.schemas.student import StudentCreate
        from app.models.student import Gender

        data = StudentCreate(
            registration_number="REG-FULL",
            first_name="Full",
            last_name="Student",
            date_of_birth=date(2010, 1, 1),
            gender=Gender.FEMALE,
            email="full@test.com",
            phone="+224 123 456",
            address="123 Main St",
            city="Conakry",
            level="6ème",
            class_name="6ème A",
            academic_year="2025-2026",
            photo_url="https://cdn.example.com/photo.jpg",
            parent_name="Parent Name",
            parent_phone="+224 654 321",
            parent_email="parent@test.com",
        )
        assert data.phone == "+224 123 456"
        assert data.level == "6ème"
        assert data.parent_name == "Parent Name"


# ─── StudentUpdate Tests ────────────────────────────────────────────────────

@pytest.mark.unit
class TestStudentUpdateSchema:
    """Tests for the StudentUpdate Pydantic schema."""

    def test_student_update_all_optional(self):
        """StudentUpdate accepts an empty body (all fields optional)."""
        from app.schemas.student import StudentUpdate

        data = StudentUpdate()
        assert data.first_name is None
        assert data.last_name is None
        assert data.email is None

    def test_student_update_partial(self):
        """StudentUpdate accepts partial updates."""
        from app.schemas.student import StudentUpdate

        data = StudentUpdate(first_name="NewFirst")
        assert data.first_name == "NewFirst"
        assert data.last_name is None

    def test_student_update_multiple_fields(self):
        """StudentUpdate accepts multiple fields at once."""
        from app.schemas.student import StudentUpdate
        from app.models.student import StudentStatus

        data = StudentUpdate(
            first_name="Updated",
            last_name="Name",
            status=StudentStatus.GRADUATED,
        )
        assert data.first_name == "Updated"
        assert data.status == StudentStatus.GRADUATED

    def test_student_update_validates_email(self):
        """StudentUpdate validates email even when optional."""
        from app.schemas.student import StudentUpdate

        with pytest.raises(ValidationError) as exc_info:
            StudentUpdate(email="not-valid-email")
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if e["loc"][-1] == "email"]
        assert len(email_errors) > 0

    def test_student_update_rejects_empty_first_name(self):
        """StudentUpdate rejects empty first_name (min_length=1 when provided)."""
        from app.schemas.student import StudentUpdate

        with pytest.raises(ValidationError) as exc_info:
            StudentUpdate(first_name="")
        errors = exc_info.value.errors()
        fn_errors = [e for e in errors if e["loc"][-1] == "first_name"]
        assert len(fn_errors) > 0

    def test_student_update_exclude_unset(self):
        """StudentUpdate.model_dump(exclude_unset=True) only includes provided fields."""
        from app.schemas.student import StudentUpdate

        data = StudentUpdate(first_name="NewFirst", status=None)
        dumped = data.model_dump(exclude_unset=True)

        # Only first_name should be in the dump (status=None was explicitly set)
        assert "first_name" in dumped
        assert "last_name" not in dumped

    def test_student_update_status_enum(self):
        """StudentUpdate accepts valid status enum values."""
        from app.schemas.student import StudentUpdate
        from app.models.student import StudentStatus

        for status in StudentStatus:
            data = StudentUpdate(status=status)
            assert data.status == status


# ─── PaymentCreate Tests ────────────────────────────────────────────────────

@pytest.mark.unit
class TestPaymentCreateSchema:
    """Tests for the PaymentCreate Pydantic schema."""

    def test_valid_payment_create(self):
        """PaymentCreate accepts all required fields with valid data."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        data = PaymentCreate(
            student_id=uuid.uuid4(),
            amount=50000.0,
            currency="GNF",
            payment_date=date(2026, 1, 15),
            payment_method=PaymentMethod.CASH,
        )
        assert data.amount == 50000.0
        assert data.payment_method == PaymentMethod.CASH

    def test_payment_create_requires_student_id(self):
        """PaymentCreate fails without student_id."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                amount=50000.0,
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "student_id" in field_names

    def test_payment_create_requires_amount(self):
        """PaymentCreate fails without amount."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id=uuid.uuid4(),
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "amount" in field_names

    def test_payment_create_requires_payment_method(self):
        """PaymentCreate fails without payment_method."""
        from app.schemas.payment import PaymentCreate

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id=uuid.uuid4(),
                amount=50000.0,
                payment_date=date(2026, 1, 15),
            )
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "payment_method" in field_names

    def test_payment_create_amount_must_be_positive(self):
        """PaymentCreate rejects zero or negative amounts (gt=0)."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id=uuid.uuid4(),
                amount=0,
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        amount_errors = [e for e in errors if e["loc"][-1] == "amount"]
        assert len(amount_errors) > 0

    def test_payment_create_negative_amount_rejected(self):
        """PaymentCreate rejects negative amounts."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id=uuid.uuid4(),
                amount=-100.0,
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        amount_errors = [e for e in errors if e["loc"][-1] == "amount"]
        assert len(amount_errors) > 0

    def test_payment_create_default_currency(self):
        """PaymentCreate defaults currency to GNF."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        data = PaymentCreate(
            student_id=uuid.uuid4(),
            amount=50000.0,
            payment_date=date(2026, 1, 15),
            payment_method=PaymentMethod.MOBILE_MONEY,
        )
        assert data.currency == "GNF"

    def test_payment_create_currency_max_length(self):
        """PaymentCreate rejects currency longer than 3 characters."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id=uuid.uuid4(),
                amount=50000.0,
                currency="TOOLONG",
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        curr_errors = [e for e in errors if e["loc"][-1] == "currency"]
        assert len(curr_errors) > 0

    def test_payment_create_optional_fields(self):
        """PaymentCreate accepts optional invoice_id and transaction_id."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        inv_id = uuid.uuid4()
        data = PaymentCreate(
            student_id=uuid.uuid4(),
            amount=50000.0,
            payment_date=date(2026, 1, 15),
            payment_method=PaymentMethod.BANK_TRANSFER,
            invoice_id=inv_id,
            transaction_id="TXN-123456",
            notes="Tuition payment Q1",
        )
        assert data.invoice_id == inv_id
        assert data.transaction_id == "TXN-123456"
        assert data.notes == "Tuition payment Q1"

    def test_payment_create_invalid_student_id_format(self):
        """PaymentCreate rejects invalid UUID for student_id."""
        from app.schemas.payment import PaymentCreate
        from app.models.payment import PaymentMethod

        with pytest.raises(ValidationError) as exc_info:
            PaymentCreate(
                student_id="not-a-uuid",
                amount=50000.0,
                payment_date=date(2026, 1, 15),
                payment_method=PaymentMethod.CASH,
            )
        errors = exc_info.value.errors()
        sid_errors = [e for e in errors if e["loc"][-1] == "student_id"]
        assert len(sid_errors) > 0


# ─── GradeCreate Tests ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestGradeCreateSchema:
    """Tests for the GradeCreate Pydantic schema."""

    def test_valid_grade_create(self):
        """GradeCreate accepts all required fields with valid data."""
        from app.schemas.grade import GradeCreate

        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=16.5,
            max_score=20.0,
            coefficient=2.0,
        )
        assert data.score == 16.5
        assert data.max_score == 20.0

    def test_grade_create_requires_student_id(self):
        """GradeCreate fails without student_id."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(score=15.0)
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "student_id" in field_names

    def test_grade_create_requires_score(self):
        """GradeCreate fails without score."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(student_id=uuid.uuid4())
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "score" in field_names

    def test_grade_create_score_must_be_non_negative(self):
        """GradeCreate rejects negative scores (ge=0)."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(
                student_id=uuid.uuid4(),
                score=-5.0,
            )
        errors = exc_info.value.errors()
        score_errors = [e for e in errors if e["loc"][-1] == "score"]
        assert len(score_errors) > 0

    def test_grade_create_score_zero_allowed(self):
        """GradeCreate accepts score=0 (ge=0 allows zero)."""
        from app.schemas.grade import GradeCreate

        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=0.0,
        )
        assert data.score == 0.0

    def test_grade_create_max_score_must_be_positive(self):
        """GradeCreate rejects max_score <= 0 (gt=0)."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(
                student_id=uuid.uuid4(),
                score=10.0,
                max_score=0,
            )
        errors = exc_info.value.errors()
        ms_errors = [e for e in errors if e["loc"][-1] == "max_score"]
        assert len(ms_errors) > 0

    def test_grade_create_negative_max_score_rejected(self):
        """GradeCreate rejects negative max_score."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(
                student_id=uuid.uuid4(),
                score=10.0,
                max_score=-20.0,
            )
        errors = exc_info.value.errors()
        ms_errors = [e for e in errors if e["loc"][-1] == "max_score"]
        assert len(ms_errors) > 0

    def test_grade_create_default_max_score(self):
        """GradeCreate defaults max_score to 20.0."""
        from app.schemas.grade import GradeCreate

        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=15.0,
        )
        assert data.max_score == 20.0

    def test_grade_create_default_coefficient(self):
        """GradeCreate defaults coefficient to 1.0."""
        from app.schemas.grade import GradeCreate

        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=15.0,
        )
        assert data.coefficient == 1.0

    def test_grade_create_coefficient_must_be_positive(self):
        """GradeCreate rejects coefficient <= 0 (gt=0)."""
        from app.schemas.grade import GradeCreate

        with pytest.raises(ValidationError) as exc_info:
            GradeCreate(
                student_id=uuid.uuid4(),
                score=15.0,
                coefficient=0,
            )
        errors = exc_info.value.errors()
        coef_errors = [e for e in errors if e["loc"][-1] == "coefficient"]
        assert len(coef_errors) > 0

    def test_grade_create_high_score_allowed(self):
        """GradeCreate allows score > max_score (business logic, not schema)."""
        from app.schemas.grade import GradeCreate

        # Schema doesn't enforce score <= max_score; that's business logic
        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=25.0,
            max_score=20.0,
        )
        assert data.score == 25.0

    def test_grade_create_optional_fields(self):
        """GradeCreate accepts optional subject_id, assessment_id, comments."""
        from app.schemas.grade import GradeCreate

        subj_id = uuid.uuid4()
        assess_id = uuid.uuid4()
        data = GradeCreate(
            student_id=uuid.uuid4(),
            score=14.0,
            subject_id=subj_id,
            assessment_id=assess_id,
            comments="Good work",
        )
        assert data.subject_id == subj_id
        assert data.assessment_id == assess_id
        assert data.comments == "Good work"


# ─── TenantCreate Tests ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantCreateSchema:
    """Tests for the TenantCreate Pydantic schema."""

    def test_valid_tenant_create(self):
        """TenantCreate accepts all required fields."""
        from app.schemas.tenants import TenantCreate

        data = TenantCreate(
            name="École Test",
            slug="ecole-test",
            type="SCHOOL",
        )
        assert data.name == "École Test"
        assert data.slug == "ecole-test"

    def test_tenant_create_requires_name(self):
        """TenantCreate fails without name."""
        from app.schemas.tenants import TenantCreate

        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(slug="test", type="SCHOOL")
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "name" in field_names

    def test_tenant_create_requires_slug(self):
        """TenantCreate fails without slug."""
        from app.schemas.tenants import TenantCreate

        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(name="Test", type="SCHOOL")
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "slug" in field_names

    def test_tenant_create_requires_type(self):
        """TenantCreate fails without type."""
        from app.schemas.tenants import TenantCreate

        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(name="Test", slug="test")
        errors = exc_info.value.errors()
        field_names = [e["loc"][-1] for e in errors]
        assert "type" in field_names

    def test_tenant_create_default_country(self):
        """TenantCreate defaults country to GN."""
        from app.schemas.tenants import TenantCreate

        data = TenantCreate(name="Test", slug="test", type="SCHOOL")
        assert data.country == "GN"

    def test_tenant_create_default_currency(self):
        """TenantCreate defaults currency to GNF."""
        from app.schemas.tenants import TenantCreate

        data = TenantCreate(name="Test", slug="test", type="SCHOOL")
        assert data.currency == "GNF"

    def test_tenant_create_with_all_optional_fields(self):
        """TenantCreate accepts all optional fields."""
        from app.schemas.tenants import TenantCreate

        data = TenantCreate(
            name="Full School",
            slug="full-school",
            type="UNIVERSITY",
            email="info@full.edu",
            phone="+224 123 456",
            address="123 Campus Ave",
            website="https://full.edu",
            country="SN",
            currency="XOF",
        )
        assert data.email == "info@full.edu"
        assert data.country == "SN"
        assert data.currency == "XOF"

    def test_tenant_create_with_levels(self):
        """TenantCreate accepts levels list."""
        from app.schemas.tenants import TenantCreate

        data = TenantCreate(
            name="Multi-Level",
            slug="multi-level",
            type="SCHOOL",
            levels=["6ème", "5ème", "4ème", "3ème"],
        )
        assert len(data.levels) == 4
        assert "6ème" in data.levels


# ─── TenantUpdate Tests ─────────────────────────────────────────────────────

@pytest.mark.unit
class TestTenantUpdateSchema:
    """Tests for the TenantUpdate Pydantic schema."""

    def test_tenant_update_all_optional(self):
        """TenantUpdate accepts an empty body."""
        from app.schemas.tenants import TenantUpdate

        data = TenantUpdate()
        assert data.name is None
        assert data.is_active is None

    def test_tenant_update_partial(self):
        """TenantUpdate accepts partial updates."""
        from app.schemas.tenants import TenantUpdate

        data = TenantUpdate(name="New Name", is_active=False)
        assert data.name == "New Name"
        assert data.is_active is False


# ─── PaymentUpdate Tests ────────────────────────────────────────────────────

@pytest.mark.unit
class TestPaymentUpdateSchema:
    """Tests for the PaymentUpdate Pydantic schema."""

    def test_payment_update_all_optional(self):
        """PaymentUpdate accepts an empty body."""
        from app.schemas.payment import PaymentUpdate

        data = PaymentUpdate()
        assert data.amount is None
        assert data.status is None

    def test_payment_update_amount_must_be_positive(self):
        """PaymentUpdate validates amount > 0 when provided."""
        from app.schemas.payment import PaymentUpdate

        with pytest.raises(ValidationError) as exc_info:
            PaymentUpdate(amount=-50.0)
        errors = exc_info.value.errors()
        amount_errors = [e for e in errors if e["loc"][-1] == "amount"]
        assert len(amount_errors) > 0

    def test_payment_update_zero_amount_rejected(self):
        """PaymentUpdate rejects amount=0."""
        from app.schemas.payment import PaymentUpdate

        with pytest.raises(ValidationError) as exc_info:
            PaymentUpdate(amount=0)
        errors = exc_info.value.errors()
        amount_errors = [e for e in errors if e["loc"][-1] == "amount"]
        assert len(amount_errors) > 0

    def test_payment_update_valid_amount(self):
        """PaymentUpdate accepts a positive amount."""
        from app.schemas.payment import PaymentUpdate

        data = PaymentUpdate(amount=75000.0)
        assert data.amount == 75000.0


# ─── GradeUpdate Tests ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestGradeUpdateSchema:
    """Tests for the GradeUpdate Pydantic schema."""

    def test_grade_update_all_optional(self):
        """GradeUpdate accepts an empty body."""
        from app.schemas.grade import GradeUpdate

        data = GradeUpdate()
        assert data.score is None
        assert data.max_score is None

    def test_grade_update_score_non_negative(self):
        """GradeUpdate validates score >= 0 when provided."""
        from app.schemas.grade import GradeUpdate

        with pytest.raises(ValidationError) as exc_info:
            GradeUpdate(score=-1.0)
        errors = exc_info.value.errors()
        score_errors = [e for e in errors if e["loc"][-1] == "score"]
        assert len(score_errors) > 0

    def test_grade_update_max_score_positive(self):
        """GradeUpdate validates max_score > 0 when provided."""
        from app.schemas.grade import GradeUpdate

        with pytest.raises(ValidationError) as exc_info:
            GradeUpdate(max_score=0)
        errors = exc_info.value.errors()
        ms_errors = [e for e in errors if e["loc"][-1] == "max_score"]
        assert len(ms_errors) > 0

    def test_grade_update_coefficient_positive(self):
        """GradeUpdate validates coefficient > 0 when provided."""
        from app.schemas.grade import GradeUpdate

        with pytest.raises(ValidationError) as exc_info:
            GradeUpdate(coefficient=-1.0)
        errors = exc_info.value.errors()
        coef_errors = [e for e in errors if e["loc"][-1] == "coefficient"]
        assert len(coef_errors) > 0
