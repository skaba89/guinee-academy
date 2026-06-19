# Re-export all ORM models so SQLAlchemy metadata registers them when
# anything does `from app.models import X` or `import app.models`.
# Listed explicitly in __all__ to silence F401 (re-export pattern).
from app.models.academic_year import AcademicYear
from app.models.admission import AdmissionApplication, AdmissionStatus
from app.models.assessment import Assessment
from app.models.associations import class_subjects, classroom_departments, subject_departments, subject_levels
from app.models.attendance import Attendance
from app.models.audit_log import AuditLog
from app.models.campus import Campus
from app.models.classroom import Classroom
from app.models.contract import Contract
from app.models.department import Department
from app.models.employee import Employee
from app.models.enrollment import Enrollment
from app.models.grade import Grade
from app.models.leave_request import LeaveRequest
from app.models.level import Level
from app.models.notification import Notification
from app.models.parent_student import ParentStudent
from app.models.payment import Invoice, InvoiceStatus, Payment, PaymentMethod, PaymentStatus
from app.models.payslip import Payslip
from app.models.profile import Profile
from app.models.program import Program
from app.models.public_page import PublicPage
from app.models.push_subscription import PushSubscription
from app.models.rgpd import AccountDeletionRequest, RGPDLog
from app.models.room import Room
from app.models.schedule import ScheduleSlot
from app.models.school_event import SchoolEvent
from app.models.student import Student
from app.models.student_check_in import StudentCheckIn
from app.models.subject import Subject
from app.models.tenant import Tenant
from app.models.tenant_security import TenantSecuritySettings
from app.models.term import Term
from app.models.user import User
from app.models.user_role import UserRole


__all__ = [
    "AcademicYear",
    "AccountDeletionRequest",
    "AdmissionApplication",
    "AdmissionStatus",
    "Assessment",
    "Attendance",
    "AuditLog",
    "Campus",
    "Classroom",
    "Contract",
    "Department",
    "Employee",
    "Enrollment",
    "Grade",
    "Invoice",
    "InvoiceStatus",
    "LeaveRequest",
    "Level",
    "Notification",
    "ParentStudent",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "Payslip",
    "Profile",
    "Program",
    "PublicPage",
    "PushSubscription",
    "RGPDLog",
    "Room",
    "ScheduleSlot",
    "SchoolEvent",
    "Student",
    "StudentCheckIn",
    "Subject",
    "Tenant",
    "TenantSecuritySettings",
    "Term",
    "User",
    "UserRole",
    "class_subjects",
    "classroom_departments",
    "subject_departments",
    "subject_levels",
]
