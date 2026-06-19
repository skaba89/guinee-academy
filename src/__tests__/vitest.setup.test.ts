/**
 * Vitest Setup Test
 * Verify vitest environment is properly configured
 */

import { describe, it, expect } from "vitest";

describe("Vitest Setup", () => {
  it("should have vitest configured correctly", () => {
    expect(true).toBe(true);
  });

  it("should support basic assertions", () => {
    const result = 2 + 2;
    expect(result).toBe(4);
  });

  it("should support object assertions", () => {
    const obj = { name: "Test", value: 123 };
    expect(obj).toEqual({ name: "Test", value: 123 });
  });

  it("should support array assertions", () => {
    const arr = [1, 2, 3];
    expect(arr).toContain(2);
    expect(arr.length).toBe(3);
  });

  it("should support async tests", async () => {
    const result = await Promise.resolve("success");
    expect(result).toBe("success");
  });

  it("should have localStorage mock", () => {
    // Reset the call history on getItem so the assertion is deterministic.
    (localStorage.getItem as any).mockClear();
    localStorage.setItem("test", "value");
    const retrieved = localStorage.getItem("test");
    expect(localStorage.getItem).toHaveBeenCalled();
    expect(retrieved).toBe("value");
  });
});
