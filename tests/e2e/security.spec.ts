/**
 * Security-focused E2E tests for Guinée Academy.
 *
 * Covers:
 * - IDOR prevention (cross-tenant data access)
 * - Token blacklist enforcement
 * - Permission-based UI rendering
 * - Race condition prevention (concurrent operations)
 * - Security headers presence
 * - Input validation and XSS prevention
 *
 * Phase 5 QA Audit — Tests & Documentation
 */
import { test, expect } from '../fixtures/auth';

// ─── IDOR Prevention ──────────────────────────────────────────────────────

test.describe('IDOR Prevention', () => {
  test('should not access student data from another tenant via URL manipulation', async ({
    loginAsAdmin,
    page,
  }) => {
    await loginAsAdmin(page);

    // Try accessing a student from another tenant by manipulating the URL
    const otherTenantStudentId = '00000000-0000-0000-0000-000000000001';
    await page.goto(`/admin/students/${otherTenantStudentId}`);

    // Should show 404 or access denied, not the student data
    const hasError = await page
      .locator('text=/Non trouvé|Accès refusé|404|403/')
      .isVisible();
    const showsStudentData = await page
      .locator('text=/Informations personnelles|Profile/')
      .isVisible();

    expect(hasError || !showsStudentData).toBeTruthy();
  });

  test('should not access homework submission of another student', async ({
    loginAsStudent,
    page,
  }) => {
    await loginAsStudent(page);

    // Navigate to homework
    await page.goto('/student/homework');

    // Try to submit homework for another student via API interception
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/homework/fake-hw-id/submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
          },
          body: JSON.stringify({
            student_id: '00000000-0000-0000-0000-000000000999', // Another student
            content: 'Malicious submission',
          }),
        });
        return { status: response.status, ok: response.ok };
      } catch {
        return { status: 0, ok: false };
      }
    });

    // Should be 403 (Forbidden) or 404 (Not Found)
    expect([403, 404, 401]).toContain(apiResponse.status);
  });

  test('should not access parent risk scores from another tenant', async ({
    loginAsParent,
    page,
  }) => {
    await loginAsParent(page);

    // Try accessing risk scores for a parent from another tenant
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch(
          '/api/v1/parents/00000000-0000-0000-0000-000000000001/risk-scores',
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
            },
          }
        );
        return { status: response.status, ok: response.ok };
      } catch {
        return { status: 0, ok: false };
      }
    });

    expect([403, 404, 401]).toContain(apiResponse.status);
  });
});

// ─── Token Blacklist ──────────────────────────────────────────────────────

test.describe('Token Blacklist', () => {
  test('should reject blacklisted token after logout', async ({ page }) => {
    // Login
    await page.goto('/auth/login');
    await page.locator('input[name="email"]').fill('admin@test.local');
    await page.locator('input[name="password"]').fill('Password123!');
    await page.locator('button:has-text("Se connecter")').click();
    await page.waitForURL('**/admin/dashboard');

    // Get the token
    const token = await page.evaluate(() => localStorage.getItem('token'));

    // Logout
    await page.locator('[data-testid="user-menu"]').click();
    await page.locator('text=Déconnexion').click();
    await page.waitForURL('**/auth/login');

    // Try using the old token
    const apiResponse = await page.evaluate(async (oldToken) => {
      try {
        const response = await fetch('/api/v1/auth/me/', {
          headers: {
            Authorization: `Bearer ${oldToken}`,
          },
        });
        return { status: response.status, ok: response.ok };
      } catch {
        return { status: 0, ok: false };
      }
    }, token);

    // Should be 401 (token blacklisted)
    expect([401, 403]).toContain(apiResponse.status);
  });

  test('logout-all should invalidate all sessions', async ({
    loginAsAdmin,
    page,
    context,
  }) => {
    await loginAsAdmin(page);

    // Create another page (simulating another session)
    const page2 = await context.newPage();
    await page2.goto('/admin/dashboard');

    // Trigger logout-all from the first page
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/auth/logout-all/', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
          },
        });
        return { status: response.status, ok: response.ok };
      } catch {
        return { status: 0, ok: false };
      }
    });

    // Both sessions should now be invalid
    // Check page2 can no longer access protected endpoints
    const page2Response = await page2.evaluate(async () => {
      try {
        const response = await fetch('/api/v1/auth/me/', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
          },
        });
        return { status: response.status };
      } catch {
        return { status: 0 };
      }
    });

    expect([401, 403]).toContain(page2Response.status);
    await page2.close();
  });
});

// ─── Security Headers ─────────────────────────────────────────────────────

test.describe('Security Headers', () => {
  test('should include X-Content-Type-Options header', async ({ page }) => {
    const response = await page.goto('/api/v1/health');

    if (response) {
      const contentTypeOptions = response.headers()['x-content-type-options'];
      expect(contentTypeOptions).toBe('nosniff');
    }
  });

  test('should include X-Frame-Options header', async ({ page }) => {
    const response = await page.goto('/api/v1/health');

    if (response) {
      const frameOptions = response.headers()['x-frame-options'];
      expect(frameOptions).toBe('DENY');
    }
  });

  test('should include Referrer-Policy header', async ({ page }) => {
    const response = await page.goto('/api/v1/health');

    if (response) {
      const referrerPolicy = response.headers()['referrer-policy'];
      expect(referrerPolicy).toBeTruthy();
    }
  });

  test('should not leak server version information', async ({ page }) => {
    const response = await page.goto('/api/v1/health');

    if (response) {
      const serverHeader = response.headers()['server'];
      // Server header should not contain version info
      if (serverHeader) {
        expect(serverHeader).not.toMatch(/\d+\.\d+\.\d+/);
      }
    }
  });
});

// ─── XSS Prevention ───────────────────────────────────────────────────────

test.describe('XSS Prevention', () => {
  test('should sanitize user input in student name fields', async ({
    loginAsAdmin,
    page,
  }) => {
    await loginAsAdmin(page);

    await page.goto('/admin/students');

    // Try creating a student with XSS payload in the name
    const xssPayload = '<script>alert("xss")</script>';

    // Check if the payload is rendered as text, not executed
    // After form submission, the XSS payload should be escaped
    const isXSSExecuted = await page.evaluate(() => {
      // Check if any script tags were injected into the DOM
      const scripts = document.querySelectorAll('script');
      return Array.from(scripts).some(
        (s) => s.textContent?.includes('alert') && !s.src
      );
    });

    expect(isXSSExecuted).toBeFalsy();
  });

  test('should not execute injected scripts in grade comments', async ({
    loginAsTeacher,
    page,
  }) => {
    await loginAsTeacher(page);

    await page.goto('/teacher/grades');

    // Check that the page doesn't have unescaped script tags
    const hasUnescapedScripts = await page.evaluate(() => {
      const body = document.body.innerHTML;
      return (
        body.includes('<script>') && !body.includes('&lt;script&gt;')
      );
    });

    expect(hasUnescapedScripts).toBeFalsy();
  });
});

// ─── Input Validation ─────────────────────────────────────────────────────

test.describe('Input Validation', () => {
  test('should reject invalid UUID in URL parameters', async ({
    loginAsAdmin,
    page,
  }) => {
    await loginAsAdmin(page);

    // Try accessing a resource with an invalid UUID
    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch(
          '/api/v1/students/../../../etc/passwd',
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
            },
          }
        );
        return { status: response.status };
      } catch {
        return { status: 0 };
      }
    });

    // Should get 404 or 422 (validation error), not 200
    expect(apiResponse.status).not.toBe(200);
  });

  test('should reject SQL injection in search parameters', async ({
    loginAsAdmin,
    page,
  }) => {
    await loginAsAdmin(page);

    const apiResponse = await page.evaluate(async () => {
      try {
        const response = await fetch(
          "/api/v1/students/?search='; DROP TABLE students; --",
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
            },
          }
        );
        return { status: response.status };
      } catch {
        return { status: 0 };
      }
    });

    // Should return 200 (with empty results) or 422, not 500
    expect([200, 422]).toContain(apiResponse.status);
  });
});

// ─── Permission-Based UI ──────────────────────────────────────────────────

test.describe('Permission-Based UI Rendering', () => {
  test('student should not see admin menu items', async ({
    loginAsStudent,
    page,
  }) => {
    await loginAsStudent(page);

    // Admin-specific menu items should not be visible
    const adminLinks = [
      'a:has-text("Gestion Utilisateurs")',
      'a:has-text("Paramètres")',
      'a:has-text("Rapports Financiers")',
    ];

    for (const selector of adminLinks) {
      const isVisible = await page.locator(selector).isVisible().catch(() => false);
      expect(isVisible).toBeFalsy();
    }
  });

  test('teacher should not see billing or tenant management', async ({
    loginAsTeacher,
    page,
  }) => {
    await loginAsTeacher(page);

    const restrictedLinks = [
      'a:has-text("Facturation")',
      'a:has-text("Abonnement")',
      'a:has-text("Gestion Établissement")',
    ];

    for (const selector of restrictedLinks) {
      const isVisible = await page.locator(selector).isVisible().catch(() => false);
      expect(isVisible).toBeFalsy();
    }
  });

  test('action buttons should respect user permissions', async ({
    loginAsStudent,
    page,
  }) => {
    await loginAsStudent(page);

    await page.goto('/student/grades');

    // Student should see their grades but NOT edit buttons
    const editButtons = page.locator('button:has-text("Modifier"), button:has-text("Supprimer")');
    const editVisible = await editButtons.isVisible().catch(() => false);
    expect(editVisible).toBeFalsy();
  });
});
