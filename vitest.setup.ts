/**
 * Vitest Setup File
 * Global test configuration and utilities
 */

import { expect, afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock localStorage — backed by an in-memory Map so getItem/setItem/removeItem
// behave like the real Web Storage API (getItem returns null for missing keys,
// setItem persists across calls, removeItem deletes the key).
const _lsStore = new Map<string, string>();

const localStorageMock = {
  getItem: vi.fn((key: string): string | null => {
    return _lsStore.has(key) ? _lsStore.get(key)! : null;
  }),
  setItem: vi.fn((key: string, value: string): void => {
    _lsStore.set(key, String(value));
  }),
  removeItem: vi.fn((key: string): void => {
    _lsStore.delete(key);
  }),
  clear: vi.fn((): void => {
    _lsStore.clear();
  }),
  key: vi.fn((index: number): string | null => {
    const keys = Array.from(_lsStore.keys());
    return index >= 0 && index < keys.length ? keys[index] : null;
  }),
  get length(): number {
    return _lsStore.size;
  },
};

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
});

// Suppress console errors in tests (optional)
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === "string" &&
      (args[0].includes("Warning: ReactDOM.render") ||
        args[0].includes("Not implemented: HTMLFormElement.prototype.submit"))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});
