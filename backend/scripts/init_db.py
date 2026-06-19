"""
Initialize the database with seed data for local development.
Compatible with SQLite and PostgreSQL.
"""
import sys
import os

# Ensure backend/ is on sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
import json

# ── Database connection ────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./guinee_academy.db")
_IS_SQLITE = DATABASE_URL.startswith("sqlite:")

if not _IS_SQLITE:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://"):
        if DATABASE_URL.startswith(prefix):
            DATABASE_URL = DATABASE_URL.replace(prefix, "postgresql://", 1)
            break
    if not DATABASE_URL.startswith("postgresql+psycopg://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if _IS_SQLITE else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _now():
    """Return current UTC datetime (works for both SQLite and PostgreSQL)."""
    return datetime.utcnow()


# ── Seed data ──────────────────────────────────────────────────────────────

DEFAULT_TENANT = {
    "name": "Lycée Alpha Conakry",
    "slug": "lycee-alpha",
    "type": "high_school",
    "tagline": "L'excellence éducative au service de l'avenir de la Guinée.",
    "country": "GN",
    "levels": ["7ème Année", "8ème Année", "9ème Année", "10ème Année", "11ème Année", "12ème Année"],
    "departments": [
        {
            "name": "Sciences et Mathématiques",
            "description": "Département scientifique — mathématiques, physique, chimie.",
            "subjects": ["Mathématiques", "Physique-Chimie", "Sciences de la Vie et de la Terre"]
        },
        {
            "name": "Lettres et Sciences Humaines",
            "description": "Département littéraire — français, histoire, philosophie.",
            "subjects": ["Français", "Histoire-Géographie", "Philosophie"]
        }
    ]
}


def seed():
    db = SessionLocal()
    try:
        now = _now()

        # ── 1. Create default tenant ──────────────────────────────────────
        tenant_res = db.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": DEFAULT_TENANT["slug"]}
        ).fetchone()

        if tenant_res:
            tenant_id = str(tenant_res[0])
            print(f"  Tenant already exists: {DEFAULT_TENANT['slug']} ({tenant_id[:8]}...)")
        else:
            tenant_id = str(uuid.uuid4())
            settings = {
                "landing": {
                    "tagline": DEFAULT_TENANT["tagline"],
                    "primary_color": "#1e3a5f",
                    "secondary_color": "#0ea5e9",
                    "announcements": [],
                    "show_programs": True,
                    "show_stats": True,
                    "show_gallery": True
                },
                "onboarding_completed": True,
                "onboarding_step": 4
            }
            db.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, type, is_active, settings, created_at, updated_at, country)
                    VALUES (:id, :name, :slug, :type, true, :settings, :now, :now, :country)
                """),
                {
                    "id": tenant_id, "name": DEFAULT_TENANT["name"],
                    "slug": DEFAULT_TENANT["slug"], "type": DEFAULT_TENANT["type"],
                    "settings": json.dumps(settings), "now": now,
                    "country": DEFAULT_TENANT.get("country", "GN"),
                }
            )
            print(f"  Created tenant: {DEFAULT_TENANT['slug']} ({tenant_id[:8]}...)")

        # ── 2. Ensure SUPER_ADMIN user exists ─────────────────────────────
        admin_email = os.environ.get("ADMIN_DEFAULT_EMAIL", "admin@guinee-academy.local")
        admin_res = db.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}
        ).fetchone()

        if admin_res:
            admin_id = str(admin_res[0])
            print(f"  SUPER_ADMIN user exists: {admin_email} ({admin_id[:8]}...)")
        else:
            admin_id = str(uuid.uuid4())
            # Hash the password using bcrypt directly (avoids passlib compat issue)
            import bcrypt
            admin_pw = os.environ.get("ADMIN_DEFAULT_PASSWORD", "Admin@123456")
            pw_hash = bcrypt.hashpw(admin_pw.encode(), bcrypt.gensalt()).decode()

            db.execute(
                text("""
                    INSERT INTO users (id, email, username, password_hash, first_name, last_name,
                                       is_active, is_superuser, tenant_id, created_at, updated_at,
                                       is_verified, mfa_enabled, must_change_password)
                    VALUES (:id, :email, :email, :pw, 'Super', 'Admin', TRUE, TRUE, NULL, :now, :now, FALSE, FALSE, FALSE)
                """),
                {"id": admin_id, "email": admin_email, "pw": pw_hash, "now": now}
            )
            print(f"  Created SUPER_ADMIN user: {admin_email}")

        # ── 3. Ensure SUPER_ADMIN role exists ─────────────────────────────
        role_res = db.execute(
            text("SELECT id FROM user_roles WHERE user_id = :uid AND role = 'SUPER_ADMIN'"),
            {"uid": admin_id}
        ).fetchone()

        if role_res:
            print(f"  SUPER_ADMIN role already assigned")
        else:
            db.execute(
                text("""
                    INSERT INTO user_roles (id, user_id, role, tenant_id, created_at, updated_at)
                    VALUES (:id, :uid, 'SUPER_ADMIN', NULL, :now, :now)
                """),
                {"id": str(uuid.uuid4()), "uid": admin_id, "now": now}
            )
            print(f"  Assigned SUPER_ADMIN role")

        # ── 4. Create tenant admin user ───────────────────────────────────
        ta_email = "admin@lycee-alpha.gn"
        ta_res = db.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": ta_email}
        ).fetchone()

        if ta_res:
            ta_id = str(ta_res[0])
            print(f"  Tenant admin user exists: {ta_email}")
        else:
            ta_id = str(uuid.uuid4())
            import bcrypt
            ta_pw_hash = bcrypt.hashpw("Admin@123456".encode(), bcrypt.gensalt()).decode()

            db.execute(
                text("""
                    INSERT INTO users (id, email, username, password_hash, first_name, last_name,
                                       is_active, is_superuser, tenant_id, created_at, updated_at,
                                       is_verified, mfa_enabled, must_change_password)
                    VALUES (:id, :email, :email, :pw, 'Amadou', 'Diallo', TRUE, FALSE, :tenant_id, :now, :now, FALSE, FALSE, FALSE)
                """),
                {"id": ta_id, "email": ta_email, "pw": ta_pw_hash, "tenant_id": tenant_id, "now": now}
            )

            # Assign TENANT_ADMIN role
            db.execute(
                text("""
                    INSERT INTO user_roles (id, user_id, role, tenant_id, created_at, updated_at)
                    VALUES (:id, :uid, 'TENANT_ADMIN', :tenant_id, :now, :now)
                """),
                {"id": str(uuid.uuid4()), "uid": ta_id, "tenant_id": tenant_id, "now": now}
            )
            print(f"  Created tenant admin: {ta_email} (password: Admin@123456)")

        # ── 5. Create demo teacher ────────────────────────────────────────
        teacher_email = "prof.mariam@lycee-alpha.gn"
        teacher_res = db.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": teacher_email}
        ).fetchone()

        if teacher_res:
            print(f"  Demo teacher exists: {teacher_email}")
        else:
            teacher_id = str(uuid.uuid4())
            import bcrypt
            teacher_pw_hash = bcrypt.hashpw("Teacher@123456".encode(), bcrypt.gensalt()).decode()

            db.execute(
                text("""
                    INSERT INTO users (id, email, username, password_hash, first_name, last_name,
                                       is_active, is_superuser, tenant_id, created_at, updated_at,
                                       is_verified, mfa_enabled, must_change_password)
                    VALUES (:id, :email, :email, :pw, 'Mariam', 'Touré', TRUE, FALSE, :tenant_id, :now, :now, FALSE, FALSE, FALSE)
                """),
                {"id": teacher_id, "email": teacher_email, "pw": teacher_pw_hash, "tenant_id": tenant_id, "now": now}
            )

            db.execute(
                text("""
                    INSERT INTO user_roles (id, user_id, role, tenant_id, created_at, updated_at)
                    VALUES (:id, :uid, 'TEACHER', :tenant_id, :now, :now)
                """),
                {"id": str(uuid.uuid4()), "uid": teacher_id, "tenant_id": tenant_id, "now": now}
            )
            print(f"  Created demo teacher: {teacher_email} (password: Teacher@123456)")

        # ── 6. Seed levels ────────────────────────────────────────────────
        for i, level_name in enumerate(DEFAULT_TENANT.get("levels", [])):
            l_res = db.execute(
                text("SELECT id FROM levels WHERE tenant_id = :tid AND name = :name"),
                {"tid": tenant_id, "name": level_name}
            ).fetchone()

            if not l_res:
                db.execute(
                    text("INSERT INTO levels (id, tenant_id, name, order_index, created_at, updated_at, code) VALUES (:id, :tid, :name, :idx, :now, :now, :code)"),
                    {"id": str(uuid.uuid4()), "tid": tenant_id, "name": level_name, "idx": i, "code": level_name[:10].upper(), "now": now}
                )
        print(f"  Seeded levels: {len(DEFAULT_TENANT.get('levels', []))}")

        # ── 7. Ensure academic year exists ────────────────────────────────
        ay_res = db.execute(
            text("SELECT id FROM academic_years WHERE tenant_id = :tid AND is_current = true"),
            {"tid": tenant_id}
        ).fetchone()

        if not ay_res:
            db.execute(
                text("""
                    INSERT INTO academic_years (id, tenant_id, name, code, start_date, end_date, is_current, created_at, updated_at)
                    VALUES (:id, :tid, '2025-2026', '25-26', '2025-09-01', '2026-06-30', true, :now, :now)
                """),
                {"id": str(uuid.uuid4()), "tid": tenant_id, "now": now}
            )
            print(f"  Created academic year: 2025-2026")
        else:
            print(f"  Academic year already exists")

        # ── 8. Seed departments and subjects ──────────────────────────────
        for dept_data in DEFAULT_TENANT.get("departments", []):
            d_res = db.execute(
                text("SELECT id FROM departments WHERE tenant_id = :tid AND name = :name"),
                {"tid": tenant_id, "name": dept_data["name"]}
            ).fetchone()

            dept_id = None
            if not d_res:
                dept_id = str(uuid.uuid4())
                db.execute(
                    text("INSERT INTO departments (id, tenant_id, name, description, created_at, updated_at, code) VALUES (:id, :tid, :name, :desc, :now, :now, :code)"),
                    {"id": dept_id, "tid": tenant_id, "name": dept_data["name"], "desc": dept_data["description"], "code": dept_data["name"][:10].upper(), "now": now}
                )
            else:
                dept_id = str(d_res[0])

            for subject_name in dept_data.get("subjects", []):
                s_res = db.execute(
                    text("SELECT id FROM subjects WHERE tenant_id = :tid AND name = :name"),
                    {"tid": tenant_id, "name": subject_name}
                ).fetchone()

                subject_id = None
                if not s_res:
                    subject_id = str(uuid.uuid4())
                    db.execute(
                        text("INSERT INTO subjects (id, tenant_id, name, created_at, updated_at, coefficient, code) VALUES (:id, :tid, :name, :now, :now, 1.0, :code)"),
                        {"id": subject_id, "tid": tenant_id, "name": subject_name, "code": subject_name[:10].upper(), "now": now}
                    )
                else:
                    subject_id = str(s_res[0])

                # Check if subject_departments table exists
                try:
                    link_res = db.execute(
                        text("SELECT 1 FROM subject_departments WHERE subject_id = :sid AND department_id = :did AND tenant_id = :tid"),
                        {"sid": subject_id, "did": dept_id, "tid": tenant_id}
                    ).fetchone()

                    if not link_res:
                        db.execute(
                            text("INSERT INTO subject_departments (subject_id, department_id, tenant_id) VALUES (:sid, :did, :tid)"),
                            {"sid": subject_id, "did": dept_id, "tid": tenant_id}
                        )
                except Exception:
                    pass  # Table may not exist yet

        print(f"  Seeded departments and subjects")

        # ── 9. Seed HR employees ─────────────────────────────────────────
        # Demo employees — mix of teachers, admin, support staff
        HR_EMPLOYEES = [
            # (employee_number, first_name, last_name, email, phone, job_title, department, hire_date, contract_type, gross_salary, weekly_hours, is_active)
            ("EMP-001", "Mariam",   "Touré",     "prof.mariam@lycee-alpha.gn",     "+224 620 11 22 01", "Enseignant Mathématiques",  "Sciences et Mathématiques",    "2021-09-01", "CDI", 1_200_000, 35, True),
            ("EMP-002", "Ousmane",  "Diallo",    "prof.ousmane@lycee-alpha.gn",    "+224 620 11 22 02", "Enseignant Physique-Chimie","Sciences et Mathématiques",    "2020-09-01", "CDI", 1_250_000, 35, True),
            ("EMP-003", "Aïssatou", "Barry",     "prof.aissatou@lycee-alpha.gn",   "+224 620 11 22 03", "Enseignante SVT",           "Sciences et Mathématiques",    "2022-09-01", "CDI", 1_150_000, 35, True),
            ("EMP-004", "Ibrahim",  "Camara",    "prof.ibrahim@lycee-alpha.gn",    "+224 620 11 22 04", "Enseignant Français",       "Lettres et Sciences Humaines","2019-09-01", "CDI", 1_180_000, 35, True),
            ("EMP-005", "Fatoumata","Sow",       "prof.fatoumata@lycee-alpha.gn",  "+224 620 11 22 05", "Enseignante Histoire-Géo",  "Lettres et Sciences Humaines","2021-01-15", "CDI", 1_100_000, 35, True),
            ("EMP-006", "Mamadou",  "Baldé",     "prof.mamadou@lycee-alpha.gn",    "+224 620 11 22 06", "Enseignant Philosophie",    "Lettres et Sciences Humaines","2018-09-01", "CDI", 1_300_000, 35, True),
            ("EMP-007", "Kadiatou", "Cissé",     "prof.kadiatou@lycee-alpha.gn",   "+224 620 11 22 07", "Enseignante Anglais",       "Lettres et Sciences Humaines","2022-09-01", "CDD", 1_050_000, 35, True),
            ("EMP-008", "Cheikh",   "Traoré",    "prof.cheikh@lycee-alpha.gn",     "+224 620 11 22 08", "Enseignant Arabe",          "Lettres et Sciences Humaines","2020-09-01", "CDI", 1_120_000, 35, True),
            ("EMP-009", "Adama",    "Conde",     "adama.conde@lycee-alpha.gn",     "+224 620 11 22 09", "Censeur (Surveillant)",     "Direction",                   "2017-09-01", "CDI", 1_500_000, 40, True),
            ("EMP-010", "Boubacar", "Keïta",     "boubacar.keita@lycee-alpha.gn",  "+224 620 11 22 10", "Surveillant Général",       "Direction",                   "2019-09-01", "CDI", 1_100_000, 40, True),
            ("EMP-011", "Mariama",  "Doubiya",   "mariama.doubiya@lycee-alpha.gn", "+224 620 11 22 11", "Secrétaire de Direction",   "Administration",              "2020-01-15", "CDI",   800_000, 35, True),
            ("EMP-012", "Lansana",  "Camara",    "lansana.camara@lycee-alpha.gn",  "+224 620 11 22 12", "Comptable",                 "Administration",              "2016-09-01", "CDI", 1_400_000, 35, True),
            ("EMP-013", "Ramatoulaye","Bah",     "ramatoulaye.bah@lycee-alpha.gn", "+224 620 11 22 13", "Responsable Orientation",   "Direction",                   "2023-09-01", "CDD",   950_000, 35, True),
            ("EMP-014", "Sékou",    "Touré",     "sekou.toure@lycee-alpha.gn",     "+224 620 11 22 14", "Agent d'Entretien",         "Services Généraux",           "2019-03-01", "CDI",   450_000, 40, True),
            ("EMP-015", "Mamady",   "Diarra",    "mamady.diarra@lycee-alpha.gn",   "+224 620 11 22 15", "Agent de Sécurité",         "Services Généraux",           "2021-06-01", "CDI",   420_000, 42, True),
            ("EMP-016", "Aminata",  "Sylla",     "aminata.sylla@lycee-alpha.gn",   "+224 620 11 22 16", "Infirmière Scolaire",       "Services Généraux",           "2022-09-01", "CDD",   700_000, 35, False),
        ]

        seeded_emps = 0
        seeded_contracts = 0
        for emp_data in HR_EMPLOYEES:
            (emp_num, fn, ln, email, phone, job, dept, hire, ctype, gross, hours, active) = emp_data

            existing = db.execute(
                text("SELECT id FROM employees WHERE tenant_id = :tid AND employee_number = :num"),
                {"tid": tenant_id, "num": emp_num}
            ).fetchone()

            if existing:
                emp_id = str(existing[0])
                continue

            emp_id = str(uuid.uuid4())
            db.execute(
                text("""
                    INSERT INTO employees
                        (id, tenant_id, employee_number, first_name, last_name, email, phone,
                         job_title, department, hire_date, is_active, created_at, updated_at,
                         nationality, country, city, bank_name)
                    VALUES
                        (:id, :tid, :num, :fn, :ln, :email, :phone,
                         :job, :dept, :hire, :active, :now, :now,
                         :nat, :country, :city, :bank)
                """),
                {
                    "id": emp_id, "tid": tenant_id, "num": emp_num,
                    "fn": fn, "ln": ln, "email": email, "phone": phone,
                    "job": job, "dept": dept, "hire": hire,
                    "active": 1 if active else 0, "now": now,
                    "nat": "Guinéenne", "country": "Guinée", "city": "Conakry",
                    "bank": "Ecobank Guinée",
                }
            )
            seeded_emps += 1

            # Linked employment_contract (CDI → no end date, CDD → 1-year contract)
            contract_id = str(uuid.uuid4())
            end_date = None if ctype == "CDI" else "2026-08-31"
            trial_end = "2021-02-28" if hire < "2021-01-01" else None
            db.execute(
                text("""
                    INSERT INTO employment_contracts
                        (id, tenant_id, employee_id, contract_number, contract_type,
                         start_date, end_date, trial_period_end, job_title,
                         gross_monthly_salary, weekly_hours, is_current, created_at, updated_at)
                    VALUES
                        (:id, :tid, :eid, :cnum, :ctype,
                         :start, :end, :trial, :job,
                         :gross, :hours, 1, :now, :now)
                """),
                {
                    "id": contract_id, "tid": tenant_id, "eid": emp_id,
                    "cnum": f"CTR-{emp_num.split('-')[1]}",
                    "ctype": ctype, "start": hire, "end": end_date,
                    "trial": trial_end, "job": job, "gross": gross,
                    "hours": hours, "now": now,
                }
            )
            seeded_contracts += 1

            # Two payslips per active employee (last 2 months: April & May 2026)
            if active:
                for (pm, py) in [(4, 2026), (5, 2026)]:
                    net = round(gross * 0.82, 2)
                    db.execute(
                        text("""
                            INSERT INTO payslips
                                (id, tenant_id, employee_id, period_month, period_year,
                                 gross_salary, net_salary, pay_date, is_final, created_at, updated_at)
                            VALUES
                                (:id, :tid, :eid, :pm, :py,
                                 :gross, :net, :pay_date, 'true', :now, :now)
                        """),
                        {
                            "id": str(uuid.uuid4()), "tid": tenant_id, "eid": emp_id,
                            "pm": pm, "py": py, "gross": gross, "net": net,
                            "pay_date": f"{py}-{pm:02d}-28",
                            "now": now,
                        }
                    )

        print(f"  Seeded HR: {seeded_emps} new employees, {seeded_contracts} new contracts, payslips for last 2 months")

        # ── 10. Seed leave requests (a few pending/approved/rejected) ────
        LEAVE_REQUESTS = [
            ("EMP-001", "CONGE_PAYE", "2026-04-10", "2026-04-14", 5,  "APPROVED", "Congé familial"),
            ("EMP-002", "MALADIE",    "2026-05-20", "2026-05-22", 3,  "APPROVED", "Certificat médical fourni"),
            ("EMP-005", "CONGE_PAYE", "2026-06-15", "2026-06-19", 5,  "PENDING",  "Congé annuel"),
            ("EMP-009", "CONGE_PAYE", "2026-03-10", "2026-03-12", 3,  "REJECTED", "Période d'examens — non autorisé"),
            ("EMP-011", "MALADIE",    "2026-05-01", "2026-05-03", 3,  "APPROVED", "Grippe saisonnière"),
            ("EMP-013", "CONGE_PAYE", "2026-07-01", "2026-07-10", 10, "PENDING",  "Congé d'été"),
        ]

        seeded_leaves = 0
        for lr_data in LEAVE_REQUESTS:
            (emp_num, ltype, start, end, days, status, reason) = lr_data
            emp_row = db.execute(
                text("SELECT id FROM employees WHERE tenant_id = :tid AND employee_number = :num"),
                {"tid": tenant_id, "num": emp_num}
            ).fetchone()
            if not emp_row:
                continue
            emp_id = str(emp_row[0])

            dup = db.execute(
                text("SELECT 1 FROM leave_requests WHERE tenant_id = :tid AND employee_id = :eid AND start_date = :s AND end_date = :e"),
                {"tid": tenant_id, "eid": emp_id, "s": start, "e": end}
            ).fetchone()
            if dup:
                continue

            db.execute(
                text("""
                    INSERT INTO leave_requests
                        (id, tenant_id, employee_id, leave_type, start_date, end_date,
                         total_days, status, reason, created_at, updated_at)
                    VALUES
                        (:id, :tid, :eid, :ltype, :start, :end,
                         :days, :status, :reason, :now, :now)
                """),
                {
                    "id": str(uuid.uuid4()), "tid": tenant_id, "eid": emp_id,
                    "ltype": ltype, "start": start, "end": end,
                    "days": days, "status": status, "reason": reason, "now": now,
                }
            )
            seeded_leaves += 1
        print(f"  Seeded HR: {seeded_leaves} leave requests")

        db.commit()
        print("\n✅ Seeding completed successfully!")

        # Print summary
        print("\n─── Database Summary ───")
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        tenant_count = db.execute(text("SELECT COUNT(*) FROM tenants")).scalar()
        role_count = db.execute(text("SELECT COUNT(*) FROM user_roles")).scalar()
        emp_count = db.execute(text("SELECT COUNT(*) FROM employees")).scalar()
        contract_count = db.execute(text("SELECT COUNT(*) FROM employment_contracts")).scalar()
        payslip_count = db.execute(text("SELECT COUNT(*) FROM payslips")).scalar()
        leave_count = db.execute(text("SELECT COUNT(*) FROM leave_requests")).scalar()
        print(f"  Users:               {user_count}")
        print(f"  Tenants:             {tenant_count}")
        print(f"  User Roles:          {role_count}")
        print(f"  Employees:           {emp_count}")
        print(f"  Employment Contracts:{contract_count}")
        print(f"  Payslips:            {payslip_count}")
        print(f"  Leave Requests:      {leave_count}")
        print(f"\n─── Login Credentials ───")
        print(f"  SUPER_ADMIN:  {admin_email} / Admin@123456")
        print(f"  TENANT_ADMIN: admin@lycee-alpha.gn / Admin@123456")
        print(f"  TEACHER:      prof.mariam@lycee-alpha.gn / Teacher@123456")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Initializing Guinée Academy database...\n")
    seed()
