import { describe, it, expect, vi, beforeEach } from "vitest";
import { parentsService } from "../parentsService";

// Mock apiClient so we don't make real network calls during tests.
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
  },
}));

// Import the mocked apiClient AFTER vi.mock so we can reference it.
import { apiClient } from "@/api/client";

describe("parentsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getChildren", () => {
    it("should return empty array if no parentId", async () => {
      const result = await parentsService.getChildren("");
      expect(result).toEqual([]);
      expect(apiClient.get).not.toHaveBeenCalled();
    });

    it("should return children on success", async () => {
      const mockData = [
        {
          id: "1",
          student_id: "s1",
          student: { id: "s1", first_name: "John" },
        },
      ];
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await parentsService.getChildren("p1");

      expect(apiClient.get).toHaveBeenCalledWith("/parents/children/", {
        params: { parent_id: "p1" },
      });
      expect(result).toHaveLength(1);
      expect(result[0].student.first_name).toBe("John");
    });
  });

  describe("getInvoices", () => {
    it("should return empty array if no studentIds", async () => {
      const result = await parentsService.getInvoices([]);
      expect(result).toEqual([]);
      expect(apiClient.get).not.toHaveBeenCalled();
    });

    it("should fetch invoices on success", async () => {
      const mockData = [{ id: "inv-1", amount: 100 }];
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await parentsService.getInvoices(["s1", "s2"]);

      expect(apiClient.get).toHaveBeenCalledWith("/invoices/", {
        params: { student_id: "s1,s2" },
      });
      expect(result).toEqual(mockData);
    });

    it("should fetch invoices for a specific selected student", async () => {
      const mockData = [{ id: "inv-2", amount: 200 }];
      (apiClient.get as any).mockResolvedValueOnce({ data: mockData });

      const result = await parentsService.getInvoices(["s1", "s2"], "s2");

      expect(apiClient.get).toHaveBeenCalledWith("/invoices/", {
        params: { student_id: "s2" },
      });
      expect(result).toEqual(mockData);
    });
  });
});
