import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useStudentData } from "../useStudentData";
import { useAuth } from "@/contexts/AuthContext";
import { useTenant } from "@/contexts/TenantContext";
import React from "react";

// Mock the contexts and apiClient — the hook no longer calls studentsService
// directly; instead it issues one GET /students/dashboard/ via apiClient.
vi.mock("@/contexts/AuthContext");
vi.mock("@/contexts/TenantContext");
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

describe("useStudentData Hook", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    (useAuth as any).mockReturnValue({ user: { id: "user-1" } });
    (useTenant as any).mockReturnValue({ tenant: { id: "tenant-1" } });

    // Default dashboard payload returned by the backend's
    // /students/dashboard/ endpoint.
    (apiClient.get as any).mockResolvedValue({
      data: {
        student: { id: "student-1" },
        enrollment: { class_id: "class-1" },
        grades: [],
        homework: [],
        schedule: [],
        checkInHistory: [],
        submissions: [],
      },
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should fetch all student data when user and tenant are present", async () => {
    const { result } = renderHook(() => useStudentData(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(apiClient.get).toHaveBeenCalledWith("/students/dashboard/");
    expect(result.current.studentId).toBe("student-1");
    expect(result.current.classId).toBe("class-1");
    expect(result.current.student).toEqual({ id: "student-1" });
  });

  it("should not fetch data if user or tenant is missing", async () => {
    (useAuth as any).mockReturnValue({ user: null });

    const { result } = renderHook(() => useStudentData(), { wrapper });

    // Wait a tick so any unexpected fetch would have had time to fire.
    await new Promise((r) => setTimeout(r, 10));
    expect(apiClient.get).not.toHaveBeenCalled();
    expect(result.current.studentId).toBeUndefined();
  });

  it("should expose loading state correctly", async () => {
    // Delay the mock so the query is still in flight when we check.
    (apiClient.get as any).mockReturnValue(
      new Promise((resolve) =>
        setTimeout(
          () =>
            resolve({
              data: {
                student: { id: "student-1" },
                enrollment: null,
                grades: [],
                homework: [],
                schedule: [],
                checkInHistory: [],
                submissions: [],
              },
            }),
          100
        )
      )
    );

    const { result } = renderHook(() => useStudentData(), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false), {
      timeout: 1000,
    });
  });
});
