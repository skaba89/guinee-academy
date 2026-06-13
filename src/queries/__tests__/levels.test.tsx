/**
 * Tests for Levels React Query hooks
 * Covers loading state, success state, error state, query key correctness, and mutations
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useLevels, useCreateLevel, useUpdateLevel, useDeleteLevel } from "@/queries/levels";
import type { Level } from "@/queries/levels";

// Mock apiClient
vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock useToast
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

import { apiClient } from "@/api/client";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const mockedPut = vi.mocked(apiClient.put);
const mockedDelete = vi.mocked(apiClient.delete);

// Test data
const mockLevels: Level[] = [
  { id: "level-1", name: "6ème", code: "6EME", order_index: 1 },
  { id: "level-2", name: "5ème", code: "5EME", order_index: 2 },
  { id: "level-3", name: "4ème", code: "4EME", order_index: 3 },
];

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function createWrapper() {
  const queryClient = createQueryClient();
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("useLevels", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading State ────────────────────────────────────────────────────

  it("should start in loading state", () => {
    mockedGet.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useLevels("tenant-1"), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  // ── Success State ────────────────────────────────────────────────────

  it("should return levels data on successful fetch", async () => {
    mockedGet.mockResolvedValueOnce({ data: mockLevels });
    const { result } = renderHook(() => useLevels("tenant-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockLevels);
    expect(result.current.data).toHaveLength(3);
    expect(result.current.data?.[0].name).toBe("6ème");
  });

  // ── Error State ──────────────────────────────────────────────────────

  it("should handle API errors gracefully", async () => {
    mockedGet.mockRejectedValueOnce(new Error("Network Error"));
    const { result } = renderHook(() => useLevels("tenant-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toBe("Network Error");
  });

  // ── Query Key Correctness ────────────────────────────────────────────

  it("should use correct query key with tenantId", async () => {
    mockedGet.mockResolvedValueOnce({ data: mockLevels });
    const queryClient = createQueryClient();
    const wrapper = function Wrapper({ children }: { children: React.ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    };

    renderHook(() => useLevels("tenant-1"), { wrapper });

    await waitFor(() => {
      const cached = queryClient.getQueryData(["levels", "tenant-1"]);
      expect(cached).toBeDefined();
    });
  });

  // ── Enabled / Disabled ───────────────────────────────────────────────

  it("should not fetch when tenantId is undefined", () => {
    const { result } = renderHook(() => useLevels(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it("should not fetch when tenantId is empty string", () => {
    const { result } = renderHook(() => useLevels(""), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(mockedGet).not.toHaveBeenCalled();
  });

  // ── Refetch Behavior ─────────────────────────────────────────────────

  it("should refetch data when refetch is called", async () => {
    mockedGet.mockResolvedValue({ data: mockLevels });
    const { result } = renderHook(() => useLevels("tenant-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    await result.current.refetch();

    expect(mockedGet).toHaveBeenCalledTimes(2);
  });

  it("should return updated data after refetch", async () => {
    const updatedLevels = [
      ...mockLevels,
      { id: "level-4", name: "3ème", code: "3EME", order_index: 4 },
    ];
    mockedGet
      .mockResolvedValueOnce({ data: mockLevels })
      .mockResolvedValueOnce({ data: updatedLevels });

    const { result } = renderHook(() => useLevels("tenant-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(3);

    await result.current.refetch();
    await waitFor(() => expect(result.current.data).toHaveLength(4));
  });
});

describe("useCreateLevel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call apiClient.post with correct data on mutate", async () => {
    const newLevel = {
      name: "3ème",
      code: "3EME",
      order_index: 4,
      tenant_id: "tenant-1",
    };
    const createdLevel: Level = { id: "level-4", ...newLevel };
    mockedPost.mockResolvedValueOnce({ data: createdLevel });

    const { result } = renderHook(() => useCreateLevel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(newLevel);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedPost).toHaveBeenCalledWith("/levels/", newLevel);
  });

  it("should handle creation error", async () => {
    mockedPost.mockRejectedValueOnce(new Error("Server Error"));

    const { result } = renderHook(() => useCreateLevel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: "3ème",
      tenant_id: "tenant-1",
      order_index: 1,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe("Server Error");
  });
});

describe("useUpdateLevel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call apiClient.put with correct data on mutate", async () => {
    const updateData = { id: "level-1", name: "6ème Updated" };
    const updatedLevel: Level = {
      id: "level-1",
      name: "6ème Updated",
      code: "6EME",
      order_index: 1,
    };
    mockedPut.mockResolvedValueOnce({ data: updatedLevel });

    const { result } = renderHook(() => useUpdateLevel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate(updateData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // The mutation destructures { id, ...updates }, so id is excluded from the payload
    expect(mockedPut).toHaveBeenCalledWith("/levels/level-1/", { name: "6ème Updated" });
  });
});

describe("useDeleteLevel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should call apiClient.delete with correct id on mutate", async () => {
    mockedDelete.mockResolvedValueOnce({});

    const { result } = renderHook(() => useDeleteLevel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("level-1");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedDelete).toHaveBeenCalledWith("/levels/level-1/");
  });

  it("should handle deletion error", async () => {
    mockedDelete.mockRejectedValueOnce(new Error("Cannot delete level with students"));

    const { result } = renderHook(() => useDeleteLevel(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("level-1");

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error?.message).toBe("Cannot delete level with students");
  });
});
