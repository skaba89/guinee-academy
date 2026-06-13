/**
 * Tests for useZodValidation hook
 * Covers validation, field-level validation, error management, and edge cases
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useZodValidation } from "@/hooks/useZodValidation";
import { z } from "zod";

describe("useZodValidation", () => {
  // ── Basic Validation ─────────────────────────────────────────────────

  describe("validate", () => {
    const simpleSchema = z.object({
      name: z.string().min(2, "Name must be at least 2 characters"),
      email: z.string().email("Invalid email"),
      age: z.number().min(0, "Age must be positive").max(150, "Age too high"),
    });

    it("should return isValid true for valid data", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      const validationResult = await result.current.validate({
        name: "Jean Dupont",
        email: "jean@example.com",
        age: 25,
      });

      expect(validationResult.isValid).toBe(true);
      expect(validationResult.errors).toEqual([]);
      expect(validationResult.data).toBeDefined();
      expect(validationResult.data?.name).toBe("Jean Dupont");
    });

    it("should return isValid false for invalid data", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      const validationResult = await result.current.validate({
        name: "J",
        email: "not-an-email",
        age: -5,
      });

      expect(validationResult.isValid).toBe(false);
      expect(validationResult.errors.length).toBeGreaterThan(0);
    });

    it("should set errors in state after validation failure", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      await result.current.validate({
        name: "J",
        email: "bad",
        age: -5,
      });

      await waitFor(() => {
        expect(result.current.errors.length).toBeGreaterThan(0);
      });
    });

    it("should clear errors after successful validation", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      // First, fail validation
      await result.current.validate({
        name: "J",
        email: "bad",
        age: -5,
      });

      await waitFor(() => {
        expect(result.current.errors.length).toBeGreaterThan(0);
      });

      // Then, pass validation
      await result.current.validate({
        name: "Jean",
        email: "jean@example.com",
        age: 25,
      });

      await waitFor(() => {
        expect(result.current.errors).toEqual([]);
      });
    });

    it("should report correct field paths in errors", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      const validationResult = await result.current.validate({
        name: "J",
        email: "not-an-email",
        age: -5,
      });

      expect(validationResult.isValid).toBe(false);
      const errorFields = validationResult.errors.map((e) => e.field);
      expect(errorFields).toContain("name");
      expect(errorFields).toContain("email");
      expect(errorFields).toContain("age");
    });

    it("should include error messages from schema", async () => {
      const { result } = renderHook(() => useZodValidation(simpleSchema));

      const validationResult = await result.current.validate({
        name: "J",
        email: "not-an-email",
        age: -5,
      });

      const nameError = validationResult.errors.find((e) => e.field === "name");
      const emailError = validationResult.errors.find((e) => e.field === "email");
      const ageError = validationResult.errors.find((e) => e.field === "age");

      expect(nameError?.message).toBe("Name must be at least 2 characters");
      expect(emailError?.message).toBe("Invalid email");
      expect(ageError?.message).toBe("Age must be positive");
    });
  });

  // ── Field-Level Validation ───────────────────────────────────────────

  describe("validateField", () => {
    const formSchema = z.object({
      username: z.string().min(3, "Username too short"),
      password: z.string().min(8, "Password must be at least 8 characters"),
    });

    it("should return null for valid field value", async () => {
      const { result } = renderHook(() => useZodValidation(formSchema));

      const error = await result.current.validateField("username", "john_doe");
      expect(error).toBeNull();
    });

    it("should return error message for invalid field value", async () => {
      const { result } = renderHook(() => useZodValidation(formSchema));

      const error = await result.current.validateField("username", "jo");
      expect(error).toBe("Username too short");
    });

    it("should return error for invalid password", async () => {
      const { result } = renderHook(() => useZodValidation(formSchema));

      const error = await result.current.validateField("password", "123");
      expect(error).toBe("Password must be at least 8 characters");
    });

    it("should return null for non-existent field in schema", async () => {
      const { result } = renderHook(() => useZodValidation(formSchema));

      const error = await result.current.validateField("unknown_field", "value");
      expect(error).toBeNull();
    });
  });

  // ── getFieldError ────────────────────────────────────────────────────

  describe("getFieldError", () => {
    const schema = z.object({
      title: z.string().min(1, "Title is required"),
      content: z.string().min(10, "Content too short"),
    });

    it("should return null when no errors exist", () => {
      const { result } = renderHook(() => useZodValidation(schema));
      expect(result.current.getFieldError("title")).toBeNull();
    });

    it("should return error message for field with error after validation", async () => {
      const { result } = renderHook(() => useZodValidation(schema));

      await result.current.validate({
        title: "",
        content: "short",
      });

      await waitFor(() => {
        expect(result.current.getFieldError("title")).toBe("Title is required");
        expect(result.current.getFieldError("content")).toBe("Content too short");
      });
    });

    it("should return null for field without error", async () => {
      const { result } = renderHook(() => useZodValidation(schema));

      await result.current.validate({
        title: "Valid Title",
        content: "short",
      });

      await waitFor(() => {
        expect(result.current.getFieldError("title")).toBeNull();
        expect(result.current.getFieldError("content")).toBe("Content too short");
      });
    });
  });

  // ── clearErrors ──────────────────────────────────────────────────────

  describe("clearErrors", () => {
    const schema = z.object({
      name: z.string().min(1, "Required"),
    });

    it("should clear all errors", async () => {
      const { result } = renderHook(() => useZodValidation(schema));

      await result.current.validate({ name: "" });
      await waitFor(() => {
        expect(result.current.errors.length).toBeGreaterThan(0);
      });

      act(() => {
        result.current.clearErrors();
      });

      expect(result.current.errors).toEqual([]);
    });

    it("should return null for getFieldError after clearing", async () => {
      const { result } = renderHook(() => useZodValidation(schema));

      await result.current.validate({ name: "" });
      await waitFor(() => {
        expect(result.current.getFieldError("name")).toBeTruthy();
      });

      act(() => {
        result.current.clearErrors();
      });

      expect(result.current.getFieldError("name")).toBeNull();
    });
  });

  // ── isValidating State ───────────────────────────────────────────────

  describe("isValidating state", () => {
    const schema = z.object({
      value: z.string(),
    });

    it("should not be validating initially", () => {
      const { result } = renderHook(() => useZodValidation(schema));
      expect(result.current.isValidating).toBe(false);
    });

    it("should set isValidating to false after validation completes", async () => {
      const { result } = renderHook(() => useZodValidation(schema));

      await result.current.validate({ value: "test" });

      expect(result.current.isValidating).toBe(false);
    });
  });

  // ── Nested Schema Validation ─────────────────────────────────────────

  describe("nested schema validation", () => {
    const nestedSchema = z.object({
      user: z.object({
        firstName: z.string().min(1, "First name required"),
        lastName: z.string().min(1, "Last name required"),
      }),
      address: z.object({
        street: z.string().min(1, "Street required"),
        city: z.string().min(1, "City required"),
      }),
    });

    it("should report nested error paths with dot notation", async () => {
      const { result } = renderHook(() => useZodValidation(nestedSchema));

      const validationResult = await result.current.validate({
        user: { firstName: "", lastName: "Dupont" },
        address: { street: "12 Rue Paris", city: "" },
      });

      expect(validationResult.isValid).toBe(false);
      const errorFields = validationResult.errors.map((e) => e.field);
      expect(errorFields).toContain("user.firstName");
      expect(errorFields).toContain("address.city");
    });

    it("should pass valid nested data", async () => {
      const { result } = renderHook(() => useZodValidation(nestedSchema));

      const validationResult = await result.current.validate({
        user: { firstName: "Jean", lastName: "Dupont" },
        address: { street: "12 Rue Paris", city: "Paris" },
      });

      expect(validationResult.isValid).toBe(true);
    });
  });

  // ── Edge Cases ───────────────────────────────────────────────────────

  describe("edge cases", () => {
    it("should handle empty object validation with required fields", async () => {
      const schema = z.object({
        required: z.string().min(1, "Required field"),
      });
      const { result } = renderHook(() => useZodValidation(schema));

      const validationResult = await result.current.validate({});
      expect(validationResult.isValid).toBe(false);
    });

    it("should handle extra fields gracefully (strip by default)", async () => {
      const schema = z.object({
        name: z.string(),
      });
      const { result } = renderHook(() => useZodValidation(schema));

      const validationResult = await result.current.validate({
        name: "Test",
        extra: "field",
      });

      expect(validationResult.isValid).toBe(true);
      // Zod strips extra fields by default
      expect(validationResult.data).not.toHaveProperty("extra");
    });

    it("should handle array validation within schema", async () => {
      const schema = z.object({
        items: z.array(z.string().min(1, "Item cannot be empty")).min(1, "At least one item required"),
      });
      const { result } = renderHook(() => useZodValidation(schema));

      const validResult = await result.current.validate({ items: ["apple", "banana"] });
      expect(validResult.isValid).toBe(true);

      const emptyResult = await result.current.validate({ items: [] });
      expect(emptyResult.isValid).toBe(false);

      const emptyItemResult = await result.current.validate({ items: [""] });
      expect(emptyItemResult.isValid).toBe(false);
    });

    it("should handle enum validation", async () => {
      const schema = z.object({
        role: z.enum(["ADMIN", "TEACHER", "STUDENT"], {
          errorMap: () => ({ message: "Invalid role" }),
        }),
      });
      const { result } = renderHook(() => useZodValidation(schema));

      const validResult = await result.current.validate({ role: "ADMIN" });
      expect(validResult.isValid).toBe(true);

      const invalidResult = await result.current.validate({ role: "SUPERVISOR" });
      expect(invalidResult.isValid).toBe(false);
      expect(invalidResult.errors[0].message).toBe("Invalid role");
    });

    it("should handle optional fields correctly", async () => {
      const schema = z.object({
        name: z.string().min(1, "Name required"),
        nickname: z.string().optional(),
      });
      const { result } = renderHook(() => useZodValidation(schema));

      const resultWithoutOptional = await result.current.validate({ name: "Jean" });
      expect(resultWithoutOptional.isValid).toBe(true);

      const resultWithOptional = await result.current.validate({ name: "Jean", nickname: "Johnny" });
      expect(resultWithOptional.isValid).toBe(true);
      expect(resultWithOptional.data?.nickname).toBe("Johnny");
    });
  });
});

// ============================================================================
// createFormValidator
// ============================================================================

describe("createFormValidator", () => {
  it("should be importable and usable", async () => {
    const { createFormValidator } = await import("@/hooks/useZodValidation");
    const schema = z.object({ name: z.string().min(1) });
    const validator = createFormValidator(schema);

    expect(validator).toBeDefined();
    expect(typeof validator.validate).toBe("function");
    expect(typeof validator.safeParse).toBe("function");
  });

  it("should validate data with validate method", async () => {
    const { createFormValidator } = await import("@/hooks/useZodValidation");
    const schema = z.object({ email: z.string().email() });
    const validator = createFormValidator(schema);

    const result = await validator.validate({ email: "test@example.com" });
    expect(result.email).toBe("test@example.com");
  });

  it("should throw on invalid data with validate method", async () => {
    const { createFormValidator } = await import("@/hooks/useZodValidation");
    const schema = z.object({ email: z.string().email() });
    const validator = createFormValidator(schema);

    await expect(validator.validate({ email: "not-email" })).rejects.toThrow();
  });

  it("should return safe parse result with safeParse method", async () => {
    const { createFormValidator } = await import("@/hooks/useZodValidation");
    const schema = z.object({ count: z.number() });
    const validator = createFormValidator(schema);

    const validResult = validator.safeParse({ count: 42 });
    expect(validResult.success).toBe(true);

    const invalidResult = validator.safeParse({ count: "not-a-number" });
    expect(invalidResult.success).toBe(false);
  });
});
