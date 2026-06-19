import { describe, it, expect, vi, beforeEach } from "vitest";
import { studentsService } from "../studentsService";

// Mock apiClient so no real network calls happen during tests.
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";

describe("studentsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getProfile", () => {
    it("should return profile data on success", async () => {
      const mockData = { id: "student-1", first_name: "John", last_name: "Doe" };
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await studentsService.getProfile("user-1", "tenant-1");

      expect(apiClient.get).toHaveBeenCalledWith("/students/profile/", {
        params: { user_id: "user-1", tenant_id: "tenant-1" },
      });
      expect(result).toEqual(mockData);
    });

    it("should return null if no user id or tenant id is provided", async () => {
      const result = await studentsService.getProfile("", "");
      expect(result).toBeNull();
      expect(apiClient.get).not.toHaveBeenCalled();
    });

    it("should propagate errors (caller is expected to handle)", async () => {
      (apiClient.get as any).mockRejectedValueOnce(new Error("Network Error"));

      await expect(
        studentsService.getProfile("user-1", "tenant-1")
      ).rejects.toThrow("Network Error");
    });
  });

  describe("getEnrollment", () => {
    it("should return active enrollment data", async () => {
      const mockData = { id: "enr-1", class_id: "class-1", status: "active" };
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await studentsService.getEnrollment("student-1");

      expect(apiClient.get).toHaveBeenCalledWith(
        `/students/student-1/enrollment/`,
        { params: { status: "active" } }
      );
      expect(result).toEqual(mockData);
    });

    it("should return null on error (catch path)", async () => {
      (apiClient.get as any).mockRejectedValueOnce(new Error("boom"));
      const result = await studentsService.getEnrollment("student-1");
      expect(result).toBeNull();
    });
  });

  describe("getGrades", () => {
    it("should return student grades", async () => {
      const mockData = [{ id: "grade-1", grade: 15 }];
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await studentsService.getGrades("student-1");

      expect(apiClient.get).toHaveBeenCalledWith("/grades/", {
        params: { student_id: "student-1" },
      });
      expect(result).toEqual(mockData);
    });

    it("should return empty array if no studentId", async () => {
      const result = await studentsService.getGrades("");
      expect(result).toEqual([]);
      expect(apiClient.get).not.toHaveBeenCalled();
    });
  });
});
