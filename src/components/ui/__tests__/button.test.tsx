/**
 * Tests for Button UI component
 * Covers rendering, variants, sizes, interactions, accessibility, and edge cases
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  // ── Rendering with default props ─────────────────────────────────────

  it("renders a button element by default", () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole("button", { name: /click me/i });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe("BUTTON");
  });

  it("renders children text correctly", () => {
    render(<Button>Save Changes</Button>);
    expect(screen.getByText("Save Changes")).toBeInTheDocument();
  });

  it("has default variant and size classes", () => {
    render(<Button>Default</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-primary");
    expect(btn.className).toContain("h-10");
  });

  // ── Rendering with custom variants ───────────────────────────────────

  it("applies destructive variant classes", () => {
    render(<Button variant="destructive">Delete</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-destructive");
  });

  it("applies outline variant classes", () => {
    render(<Button variant="outline">Outline</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("border-input");
  });

  it("applies secondary variant classes", () => {
    render(<Button variant="secondary">Secondary</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-secondary");
  });

  it("applies ghost variant classes", () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("hover:bg-accent");
  });

  it("applies link variant classes", () => {
    render(<Button variant="link">Link</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("text-primary");
    expect(btn.className).toContain("underline-offset-4");
  });

  it("applies hero variant classes", () => {
    render(<Button variant="hero">Hero</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("shadow-lg");
  });

  it("applies glass variant classes", () => {
    render(<Button variant="glass">Glass</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("backdrop-blur-sm");
  });

  // ── Rendering with custom sizes ──────────────────────────────────────

  it("applies sm size classes", () => {
    render(<Button size="sm">Small</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-9");
  });

  it("applies lg size classes", () => {
    render(<Button size="lg">Large</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-11");
  });

  it("applies xl size classes", () => {
    render(<Button size="xl">Extra Large</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-14");
  });

  it("applies icon size classes", () => {
    render(<Button size="icon">⚙</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-10");
    expect(btn.className).toContain("w-10");
  });

  // ── User interactions ────────────────────────────────────────────────

  it("calls onClick handler when clicked", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("does not call onClick when disabled", () => {
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Disabled</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).not.toHaveBeenCalled();
  });

  // ── Accessibility ────────────────────────────────────────────────────

  it("has correct role attribute", () => {
    render(<Button>Button</Button>);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("passes aria-label through", () => {
    render(<Button aria-label="Close dialog">✕</Button>);
    expect(screen.getByLabelText("Close dialog")).toBeInTheDocument();
  });

  it("applies disabled attribute correctly", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

  it("applies aria-disabled when provided", () => {
    render(<Button aria-disabled="true">Semi-disabled</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("aria-disabled", "true");
  });

  // ── Edge cases ───────────────────────────────────────────────────────

  it("applies disabled styling classes", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("disabled:opacity-50");
    expect(btn.className).toContain("disabled:pointer-events-none");
  });

  it("merges custom className with variant classes", () => {
    render(<Button className="my-custom-class">Custom</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("my-custom-class");
    expect(btn.className).toContain("bg-primary");
  });

  it("passes through additional HTML button attributes", () => {
    render(
      <Button type="submit" name="action" value="save" form="myForm">
        Submit
      </Button>
    );
    const btn = screen.getByRole("button");
    expect(btn).toHaveAttribute("type", "submit");
    expect(btn).toHaveAttribute("name", "action");
    expect(btn).toHaveAttribute("value", "save");
    expect(btn).toHaveAttribute("form", "myForm");
  });

  it("renders as child component when asChild is true", () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>
    );
    const link = screen.getByRole("link", { name: /link button/i });
    expect(link).toBeInTheDocument();
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("href", "/test");
    expect(link.className).toContain("bg-primary");
  });

  it("forwards ref correctly", () => {
    const ref = vi.fn();
    render(<Button ref={ref}>Ref Button</Button>);
    expect(ref).toHaveBeenCalledTimes(1);
    expect(ref).toHaveBeenCalledWith(expect.any(HTMLButtonElement));
  });

  it("has correct displayName", () => {
    expect(Button.displayName).toBe("Button");
  });

  it("renders with both variant and size simultaneously", () => {
    render(
      <Button variant="destructive" size="lg">
        Big Red Button
      </Button>
    );
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-destructive");
    expect(btn.className).toContain("h-11");
  });
});
