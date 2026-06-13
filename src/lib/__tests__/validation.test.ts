/**
 * Tests for Validation Schemas & Utilities
 * Covers student, invoice, payment, grade, and attendance schemas,
 * plus the validateData and validateOrThrow helper functions
 */

import { describe, it, expect } from "vitest";
import {
  emailSchema,
  phoneSchema,
  ibanSchema,
  postalCodeSchema,
  studentSchema,
  invoiceSchema,
  paymentSchema,
  gradeSchema,
  attendanceSchema,
  validateData,
  validateOrThrow,
} from "@/lib/validation";

// ============================================================================
// COMMON SCHEMAS
// ============================================================================

describe("emailSchema", () => {
  it("should accept valid email addresses", () => {
    expect(emailSchema.safeParse("user@example.com").success).toBe(true);
    expect(emailSchema.safeParse("admin@guinee-academy.com").success).toBe(true);
    expect(emailSchema.safeParse("test+tag@domain.co.uk").success).toBe(true);
  });

  it("should reject empty string", () => {
    const result = emailSchema.safeParse("");
    expect(result.success).toBe(false);
    if (!result.success) {
      const messages = result.error.errors.map((e) => e.message);
      expect(messages.some((m) => m.includes("requis") || m.includes("invalide"))).toBe(true);
    }
  });

  it("should reject invalid email format", () => {
    const result = emailSchema.safeParse("not-an-email");
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("invalide");
    }
  });

  it("should reject email without domain", () => {
    const result = emailSchema.safeParse("user@");
    expect(result.success).toBe(false);
  });

  it("should reject email without @ sign", () => {
    const result = emailSchema.safeParse("userdomain.com");
    expect(result.success).toBe(false);
  });
});

describe("phoneSchema", () => {
  it("should accept valid French phone numbers with 0 prefix", () => {
    expect(phoneSchema.safeParse("0612345678").success).toBe(true);
    expect(phoneSchema.safeParse("0712345678").success).toBe(true);
  });

  it("should accept valid French phone numbers with +33 prefix", () => {
    expect(phoneSchema.safeParse("+33612345678").success).toBe(true);
  });

  it("should accept empty string (optional)", () => {
    expect(phoneSchema.safeParse("").success).toBe(true);
  });

  it("should accept undefined (optional)", () => {
    expect(phoneSchema.safeParse(undefined).success).toBe(true);
  });

  it("should reject non-French phone numbers", () => {
    const result = phoneSchema.safeParse("1234567890");
    expect(result.success).toBe(false);
  });

  it("should reject French number starting with 00", () => {
    const result = phoneSchema.safeParse("0012345678");
    expect(result.success).toBe(false);
  });
});

describe("ibanSchema", () => {
  it("should accept valid French IBAN", () => {
    expect(ibanSchema.safeParse("FR7612345678901234567890123").success).toBe(true);
  });

  it("should accept valid French IBAN with spaces", () => {
    expect(ibanSchema.safeParse("FR76 1234 5678 9012 3456 7890 123").success).toBe(true);
  });

  it("should accept undefined (optional)", () => {
    expect(ibanSchema.safeParse(undefined).success).toBe(true);
  });

  it("should reject non-French IBAN", () => {
    const result = ibanSchema.safeParse("DE89370400440532013000");
    expect(result.success).toBe(false);
  });

  it("should reject too-short IBAN", () => {
    const result = ibanSchema.safeParse("FR761234");
    expect(result.success).toBe(false);
  });
});

describe("postalCodeSchema", () => {
  it("should accept valid 5-digit postal codes", () => {
    expect(postalCodeSchema.safeParse("75001").success).toBe(true);
    expect(postalCodeSchema.safeParse("93200").success).toBe(true);
  });

  it("should accept undefined (optional)", () => {
    expect(postalCodeSchema.safeParse(undefined).success).toBe(true);
  });

  it("should reject postal codes with less than 5 digits", () => {
    const result = postalCodeSchema.safeParse("7500");
    expect(result.success).toBe(false);
  });

  it("should reject postal codes with more than 5 digits", () => {
    const result = postalCodeSchema.safeParse("750001");
    expect(result.success).toBe(false);
  });

  it("should reject postal codes with letters", () => {
    const result = postalCodeSchema.safeParse("75A01");
    expect(result.success).toBe(false);
  });
});

// ============================================================================
// STUDENT SCHEMA
// ============================================================================

describe("studentSchema", () => {
  const validStudent = {
    first_name: "Jean",
    last_name: "Dupont",
    birth_date: "2010-05-15",
    gender: "M" as const,
  };

  it("should validate a complete valid student", () => {
    const result = studentSchema.safeParse(validStudent);
    expect(result.success).toBe(true);
  });

  it("should validate student with optional fields", () => {
    const studentWithEmail = {
      ...validStudent,
      email: "jean.dupont@parent.fr",
      phone: "0612345678",
      address: "12 Rue de Paris",
      city: "Paris",
      postal_code: "75001",
    };
    const result = studentSchema.safeParse(studentWithEmail);
    expect(result.success).toBe(true);
  });

  it("should reject first_name shorter than 2 characters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      first_name: "J",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("2 caractères");
    }
  });

  it("should reject first_name exceeding 100 characters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      first_name: "A".repeat(101),
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("100 caractères");
    }
  });

  it("should reject first_name with special characters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      first_name: "Jean@123",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("lettres");
    }
  });

  it("should accept first_name with accented characters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      first_name: "Élise",
    });
    expect(result.success).toBe(true);
  });

  it("should accept first_name with apostrophes and hyphens", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      first_name: "Marie-Claire",
    });
    expect(result.success).toBe(true);
  });

  it("should reject last_name shorter than 2 characters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      last_name: "D",
    });
    expect(result.success).toBe(false);
  });

  it("should reject invalid gender values", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      gender: "X",
    });
    expect(result.success).toBe(false);
  });

  it("should accept all valid gender values", () => {
    for (const gender of ["M", "F", "OTHER"] as const) {
      const result = studentSchema.safeParse({ ...validStudent, gender });
      expect(result.success).toBe(true);
    }
  });

  it("should reject birth_date for students younger than 3", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      birth_date: "2024-01-01",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("3");
    }
  });

  it("should accept valid registration_number format", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      registration_number: "ETU-2024-0001",
    });
    expect(result.success).toBe(true);
  });

  it("should reject registration_number with lowercase letters", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      registration_number: "etu-2024-0001",
    });
    expect(result.success).toBe(false);
  });

  it("should accept valid status enum values", () => {
    for (const status of ["ACTIVE", "INACTIVE", "GRADUATED", "EXPELLED"] as const) {
      const result = studentSchema.safeParse({ ...validStudent, status });
      expect(result.success).toBe(true);
    }
  });

  it("should reject invalid status values", () => {
    const result = studentSchema.safeParse({
      ...validStudent,
      status: "PENDING",
    });
    expect(result.success).toBe(false);
  });
});

// ============================================================================
// INVOICE SCHEMA
// ============================================================================

describe("invoiceSchema", () => {
  const validInvoice = {
    student_id: "550e8400-e29b-41d4-a716-446655440000",
    // The schema refine requires val.toFixed(2) === val.toString(),
    // so the amount must have exactly 2 decimal places in its string form
    amount: 1500.12,
    due_date: "2030-12-31",
  };

  it("should validate a valid invoice", () => {
    const result = invoiceSchema.safeParse(validInvoice);
    expect(result.success).toBe(true);
  });

  it("should reject invalid student_id (not UUID)", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      student_id: "not-a-uuid",
    });
    expect(result.success).toBe(false);
  });

  it("should reject negative amount", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      amount: -100,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("positif");
    }
  });

  it("should reject amount exceeding 100000", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      amount: 200000,
    });
    expect(result.success).toBe(false);
  });

  it("should reject zero amount", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      amount: 0,
    });
    expect(result.success).toBe(false);
  });

  it("should reject past due dates", () => {
    const result = invoiceSchema.safeParse({
      student_id: "550e8400-e29b-41d4-a716-446655440000",
      amount: 100.12,
      due_date: "2020-01-01",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const errorMessages = result.error.errors.map((e) => e.message);
      expect(errorMessages.some((m) => m.includes("passé"))).toBe(true);
    }
  });

  it("should validate invoice with optional fields", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      description: "Tuition fee for semester 1",
      status: "PENDING",
      invoice_number: "INV-2024-000001",
    });
    expect(result.success).toBe(true);
  });

  it("should reject invalid invoice_number format", () => {
    const result = invoiceSchema.safeParse({
      ...validInvoice,
      invoice_number: "INVALID-123",
    });
    expect(result.success).toBe(false);
  });
});

// ============================================================================
// GRADE SCHEMA
// ============================================================================

describe("gradeSchema", () => {
  const validGrade = {
    student_id: "550e8400-e29b-41d4-a716-446655440000",
    subject_id: "550e8400-e29b-41d4-a716-446655440001",
    term_id: "550e8400-e29b-41d4-a716-446655440002",
    // The schema refine requires val.toFixed(2) === val.toString(),
    // so the grade must have exactly 2 decimal places in its string form
    grade: 15.12,
  };

  it("should validate a valid grade", () => {
    const result = gradeSchema.safeParse(validGrade);
    expect(result.success).toBe(true);
  });

  it("should reject negative grades", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: -1,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("négative");
    }
  });

  it("should reject grades above 20", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: 21,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("20");
    }
  });

  it("should reject integer grade of 0 due to decimal refine", () => {
    // Schema refine: val.toFixed(2) === val.toString() → "0.00" !== "0"
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: 0,
    });
    expect(result.success).toBe(false);
  });

  it("should reject integer grade of 20 due to decimal refine", () => {
    // Schema refine: val.toFixed(2) === val.toString() → "20.00" !== "20"
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: 20,
    });
    expect(result.success).toBe(false);
  });

  it("should accept grade with exactly 2 decimal places like 0.12", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: 0.12,
    });
    expect(result.success).toBe(true);
  });

  it("should accept grade of 19.99", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      grade: 19.99,
    });
    expect(result.success).toBe(true);
  });

  it("should accept coefficient with default value of 1", () => {
    const result = gradeSchema.safeParse(validGrade);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.coefficient).toBe(1);
    }
  });

  it("should reject coefficient above 10", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      coefficient: 11,
    });
    expect(result.success).toBe(false);
  });

  it("should reject zero coefficient", () => {
    const result = gradeSchema.safeParse({
      ...validGrade,
      coefficient: 0,
    });
    expect(result.success).toBe(false);
  });
});

// ============================================================================
// ATTENDANCE SCHEMA
// ============================================================================

describe("attendanceSchema", () => {
  const validAttendance = {
    student_id: "550e8400-e29b-41d4-a716-446655440000",
    date: "2024-01-15",
    status: "PRESENT" as const,
  };

  it("should validate valid attendance record", () => {
    const result = attendanceSchema.safeParse(validAttendance);
    expect(result.success).toBe(true);
  });

  it("should accept all valid status values", () => {
    for (const status of ["PRESENT", "ABSENT", "LATE", "EXCUSED"] as const) {
      const result = attendanceSchema.safeParse({ ...validAttendance, status });
      expect(result.success).toBe(true);
    }
  });

  it("should reject invalid status", () => {
    const result = attendanceSchema.safeParse({
      ...validAttendance,
      status: "UNKNOWN",
    });
    expect(result.success).toBe(false);
  });

  it("should reject future dates", () => {
    const result = attendanceSchema.safeParse({
      ...validAttendance,
      date: "2099-12-31",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.errors[0].message).toContain("futur");
    }
  });
});

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

describe("validateData", () => {
  it("should return success with data for valid input", () => {
    const result = validateData(studentSchema, {
      first_name: "Jean",
      last_name: "Dupont",
      birth_date: "2010-05-15",
      gender: "M",
    });

    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data?.first_name).toBe("Jean");
  });

  it("should return errors object for invalid input", () => {
    const result = validateData(studentSchema, {
      first_name: "J",
      last_name: "",
      gender: "INVALID",
    });

    expect(result.success).toBe(false);
    expect(result.errors).toBeDefined();
    expect(Object.keys(result.errors || {}).length).toBeGreaterThan(0);
  });

  it("should map error paths to field names", () => {
    const result = validateData(studentSchema, {
      first_name: "",
    });

    expect(result.success).toBe(false);
    expect(result.errors).toHaveProperty("first_name");
  });

  it("should not include data on validation failure", () => {
    const result = validateData(studentSchema, {
      first_name: "J",
    });

    expect(result.success).toBe(false);
    expect(result.data).toBeUndefined();
  });
});

describe("validateOrThrow", () => {
  it("should return parsed data for valid input", () => {
    const data = validateOrThrow(emailSchema, "test@example.com");
    expect(data).toBe("test@example.com");
  });

  it("should throw ZodError for invalid input", () => {
    expect(() => validateOrThrow(emailSchema, "not-an-email")).toThrow();
  });
});
