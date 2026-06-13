/**
 * Tests for App Store (Zustand)
 * Covers initial state, state mutations, role-based access, notifications, theme, and reset
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { useAppStore } from "@/stores/appStore";
import type { User, Tenant, Permission } from "@/stores/types";

describe("AppStore", () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAppStore.getState().reset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  // ── Initial State ────────────────────────────────────────────────────

  describe("initial state", () => {
    it("should have null user by default", () => {
      expect(useAppStore.getState().user).toBeNull();
    });

    it("should have null currentTenant by default", () => {
      expect(useAppStore.getState().currentTenant).toBeNull();
    });

    it("should have empty tenants array by default", () => {
      expect(useAppStore.getState().tenants).toEqual([]);
    });

    it("should have empty permissions by default", () => {
      expect(useAppStore.getState().permissions).toEqual([]);
    });

    it("should have sidebarOpen true by default", () => {
      expect(useAppStore.getState().sidebarOpen).toBe(true);
    });

    it("should have light theme by default", () => {
      expect(useAppStore.getState().theme).toBe("light");
    });

    it("should have empty notifications by default", () => {
      expect(useAppStore.getState().notifications).toEqual([]);
    });

    it("should not be authenticated by default", () => {
      expect(useAppStore.getState().isAuthenticated).toBe(false);
    });

    it("should not be loading by default", () => {
      expect(useAppStore.getState().isLoading).toBe(false);
    });
  });

  // ── User State ───────────────────────────────────────────────────────

  describe("setUser", () => {
    it("should set a user", () => {
      const user: User = {
        id: "user-1",
        email: "admin@guinee-academy.com",
        first_name: "Admin",
        last_name: "User",
        is_active: true,
      };
      useAppStore.getState().setUser(user);
      expect(useAppStore.getState().user).toEqual(user);
    });

    it("should clear user when set to null", () => {
      const user: User = {
        id: "user-1",
        email: "admin@guinee-academy.com",
        first_name: "Admin",
        last_name: "User",
        is_active: true,
      };
      useAppStore.getState().setUser(user);
      useAppStore.getState().setUser(null);
      expect(useAppStore.getState().user).toBeNull();
    });
  });

  // ── Tenant State ─────────────────────────────────────────────────────

  describe("setCurrentTenant", () => {
    it("should set current tenant", () => {
      const tenant: Tenant = {
        id: "tenant-1",
        name: "École Primaire",
        slug: "ecole-primaire",
        is_active: true,
      };
      useAppStore.getState().setCurrentTenant(tenant);
      expect(useAppStore.getState().currentTenant).toEqual(tenant);
    });

    it("should clear current tenant when set to null", () => {
      const tenant: Tenant = {
        id: "tenant-1",
        name: "École Primaire",
        slug: "ecole-primaire",
        is_active: true,
      };
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setCurrentTenant(null);
      expect(useAppStore.getState().currentTenant).toBeNull();
    });
  });

  describe("setTenants", () => {
    it("should set tenants list", () => {
      const tenants: Tenant[] = [
        { id: "t1", name: "School A", slug: "school-a", is_active: true },
        { id: "t2", name: "School B", slug: "school-b", is_active: true },
      ];
      useAppStore.getState().setTenants(tenants);
      expect(useAppStore.getState().tenants).toEqual(tenants);
      expect(useAppStore.getState().tenants).toHaveLength(2);
    });
  });

  // ── Permissions & Roles ──────────────────────────────────────────────

  describe("hasRole", () => {
    const tenant: Tenant = {
      id: "tenant-1",
      name: "Test School",
      slug: "test-school",
      is_active: true,
    };

    it("should return false when no current tenant", () => {
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "SUPER_ADMIN" },
      ]);
      expect(useAppStore.getState().hasRole("SUPER_ADMIN")).toBe(false);
    });

    it("should return true when user has the role for current tenant", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TENANT_ADMIN" },
      ]);
      expect(useAppStore.getState().hasRole("TENANT_ADMIN")).toBe(true);
    });

    it("should return false when user does not have the role", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TEACHER" },
      ]);
      expect(useAppStore.getState().hasRole("TENANT_ADMIN")).toBe(false);
    });

    it("should return false when role is for a different tenant", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "other-tenant", user_id: "u1", role: "TENANT_ADMIN" },
      ]);
      expect(useAppStore.getState().hasRole("TENANT_ADMIN")).toBe(false);
    });
  });

  describe("hasAnyRole", () => {
    const tenant: Tenant = {
      id: "tenant-1",
      name: "Test School",
      slug: "test-school",
      is_active: true,
    };

    it("should return true when user has any of the specified roles", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TEACHER" },
      ]);
      expect(useAppStore.getState().hasAnyRole(["TENANT_ADMIN", "TEACHER"])).toBe(true);
    });

    it("should return false when user has none of the specified roles", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "STUDENT" },
      ]);
      expect(useAppStore.getState().hasAnyRole(["TENANT_ADMIN", "TEACHER"])).toBe(false);
    });
  });

  describe("isAdmin", () => {
    const tenant: Tenant = {
      id: "tenant-1",
      name: "Test School",
      slug: "test-school",
      is_active: true,
    };

    it("should return true for SUPER_ADMIN", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "SUPER_ADMIN" },
      ]);
      expect(useAppStore.getState().isAdmin()).toBe(true);
    });

    it("should return true for TENANT_ADMIN", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TENANT_ADMIN" },
      ]);
      expect(useAppStore.getState().isAdmin()).toBe(true);
    });

    it("should return true for DIRECTOR", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "DIRECTOR" },
      ]);
      expect(useAppStore.getState().isAdmin()).toBe(true);
    });

    it("should return false for non-admin roles", () => {
      useAppStore.getState().setCurrentTenant(tenant);
      useAppStore.getState().setPermissions([
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TEACHER" },
      ]);
      expect(useAppStore.getState().isAdmin()).toBe(false);
    });
  });

  // ── Sidebar State ────────────────────────────────────────────────────

  describe("sidebar", () => {
    it("should toggle sidebar state", () => {
      expect(useAppStore.getState().sidebarOpen).toBe(true);
      useAppStore.getState().toggleSidebar();
      expect(useAppStore.getState().sidebarOpen).toBe(false);
      useAppStore.getState().toggleSidebar();
      expect(useAppStore.getState().sidebarOpen).toBe(true);
    });

    it("should set sidebar open explicitly", () => {
      useAppStore.getState().setSidebarOpen(false);
      expect(useAppStore.getState().sidebarOpen).toBe(false);
      useAppStore.getState().setSidebarOpen(true);
      expect(useAppStore.getState().sidebarOpen).toBe(true);
    });
  });

  // ── Theme State ──────────────────────────────────────────────────────

  describe("setTheme", () => {
    it("should set theme to dark", () => {
      useAppStore.getState().setTheme("dark");
      expect(useAppStore.getState().theme).toBe("dark");
    });

    it("should set theme to light", () => {
      useAppStore.getState().setTheme("dark");
      useAppStore.getState().setTheme("light");
      expect(useAppStore.getState().theme).toBe("light");
    });

    it("should persist theme to localStorage", () => {
      useAppStore.getState().setTheme("dark");
      expect(localStorage.setItem).toHaveBeenCalledWith("theme", "dark");
    });

    it("should add dark class to document element for dark theme", () => {
      useAppStore.getState().setTheme("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should remove dark class from document element for light theme", () => {
      document.documentElement.classList.add("dark");
      useAppStore.getState().setTheme("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  // ── Notifications ────────────────────────────────────────────────────

  describe("addNotification", () => {
    it("should add a notification with generated id and timestamp", () => {
      const before = Date.now();
      useAppStore.getState().addNotification({
        type: "success",
        message: "Operation succeeded",
      });
      const after = Date.now();

      const { notifications } = useAppStore.getState();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe("success");
      expect(notifications[0].message).toBe("Operation succeeded");
      expect(notifications[0].id).toBeTruthy();
      expect(notifications[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(notifications[0].timestamp).toBeLessThanOrEqual(after);
    });

    it("should add notification with optional description", () => {
      useAppStore.getState().addNotification({
        type: "error",
        message: "Something failed",
        description: "Details about the error",
      });

      const { notifications } = useAppStore.getState();
      expect(notifications[0].description).toBe("Details about the error");
    });

    it("should auto-remove notification after default duration (5s)", () => {
      useAppStore.getState().addNotification({
        type: "info",
        message: "Auto-dismiss",
      });

      expect(useAppStore.getState().notifications).toHaveLength(1);
      vi.advanceTimersByTime(5000);
      expect(useAppStore.getState().notifications).toHaveLength(0);
    });

    it("should auto-remove notification after custom duration", () => {
      useAppStore.getState().addNotification({
        type: "warning",
        message: "Custom duration",
        duration: 3000,
      });

      expect(useAppStore.getState().notifications).toHaveLength(1);
      vi.advanceTimersByTime(2999);
      expect(useAppStore.getState().notifications).toHaveLength(1);
      vi.advanceTimersByTime(1);
      expect(useAppStore.getState().notifications).toHaveLength(0);
    });

    it("should not auto-remove notification when duration is 0", () => {
      useAppStore.getState().addNotification({
        type: "info",
        message: "Persistent",
        duration: 0,
      });

      vi.advanceTimersByTime(60000);
      expect(useAppStore.getState().notifications).toHaveLength(1);
    });
  });

  describe("removeNotification", () => {
    it("should remove notification by id", () => {
      useAppStore.getState().addNotification({ type: "success", message: "First" });
      useAppStore.getState().addNotification({ type: "error", message: "Second" });

      const { notifications } = useAppStore.getState();
      const idToRemove = notifications[0].id;

      useAppStore.getState().removeNotification(idToRemove);
      expect(useAppStore.getState().notifications).toHaveLength(1);
      expect(useAppStore.getState().notifications[0].message).toBe("Second");
    });
  });

  describe("clearNotifications", () => {
    it("should clear all notifications", () => {
      useAppStore.getState().addNotification({ type: "success", message: "One" });
      useAppStore.getState().addNotification({ type: "error", message: "Two" });
      useAppStore.getState().addNotification({ type: "info", message: "Three" });

      useAppStore.getState().clearNotifications();
      expect(useAppStore.getState().notifications).toHaveLength(0);
    });
  });

  // ── Auth State ───────────────────────────────────────────────────────

  describe("setIsAuthenticated", () => {
    it("should set authentication state", () => {
      useAppStore.getState().setIsAuthenticated(true);
      expect(useAppStore.getState().isAuthenticated).toBe(true);
      useAppStore.getState().setIsAuthenticated(false);
      expect(useAppStore.getState().isAuthenticated).toBe(false);
    });
  });

  describe("setIsLoading", () => {
    it("should set loading state", () => {
      useAppStore.getState().setIsLoading(true);
      expect(useAppStore.getState().isLoading).toBe(true);
      useAppStore.getState().setIsLoading(false);
      expect(useAppStore.getState().isLoading).toBe(false);
    });
  });

  // ── Batch Auth Sync ──────────────────────────────────────────────────

  describe("syncAuth", () => {
    it("should batch update auth-related state in a single mutation", () => {
      const user: User = {
        id: "user-1",
        email: "admin@guinee-academy.com",
        first_name: "Admin",
        last_name: "User",
        is_active: true,
      };
      const tenant: Tenant = {
        id: "tenant-1",
        name: "Test School",
        slug: "test-school",
        is_active: true,
      };
      const permissions: Permission[] = [
        { id: "p1", tenant_id: "tenant-1", user_id: "u1", role: "TENANT_ADMIN" },
      ];

      useAppStore.getState().syncAuth({
        user,
        currentTenant: tenant,
        isAuthenticated: true,
        isLoading: false,
        permissions,
      });

      const state = useAppStore.getState();
      expect(state.user).toEqual(user);
      expect(state.currentTenant).toEqual(tenant);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(state.permissions).toEqual(permissions);
    });
  });

  // ── Reset ────────────────────────────────────────────────────────────

  describe("reset", () => {
    it("should reset all state to initial values", () => {
      // Set various state values
      useAppStore.getState().setUser({
        id: "user-1",
        email: "admin@guinee-academy.com",
        first_name: "Admin",
        last_name: "User",
        is_active: true,
      });
      useAppStore.getState().setCurrentTenant({
        id: "tenant-1",
        name: "Test School",
        slug: "test-school",
        is_active: true,
      });
      useAppStore.getState().setIsAuthenticated(true);
      useAppStore.getState().setIsLoading(true);
      useAppStore.getState().setTheme("dark");
      useAppStore.getState().addNotification({ type: "success", message: "Test" });

      // Reset
      useAppStore.getState().reset();

      const state = useAppStore.getState();
      expect(state.user).toBeNull();
      expect(state.currentTenant).toBeNull();
      expect(state.tenants).toEqual([]);
      expect(state.permissions).toEqual([]);
      expect(state.sidebarOpen).toBe(true);
      expect(state.theme).toBe("light");
      expect(state.notifications).toEqual([]);
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
    });
  });
});
