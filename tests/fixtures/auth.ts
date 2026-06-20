import { test as base } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Fixture pour l'authentification
 * 
 * Permet de tester les fonctionnalités sans avoir à se reconnecter à chaque fois
 */

type AuthFixture = {
  authenticatedPage: Page;
  loginAs: (page: Page, email: string, password: string) => Promise<void>;
  loginAsAdmin: (page: Page) => Promise<void>;
  loginAsTeacher: (page: Page) => Promise<void>;
  loginAsParent: (page: Page) => Promise<void>;
  loginAsStudent: (page: Page) => Promise<void>;
};

export const test = base.extend<AuthFixture>({
  authenticatedPage: async ({ page }, use) => {
    // Se connecter avant chaque test
    await page.goto('/auth/login');
    
    // Utiliser les identifiants de test
    await page.locator('input[name="email"]').fill('admin@test.local');
    await page.locator('input[name="password"]').fill('Password123!');

    await page.locator('button:has-text("Se connecter")').click();
    
    // Attendre la redirection vers le dashboard admin (URL: /{tenantSlug}/admin)
    await page.waitForURL(/\/[^/]+\/admin$/);
    
    await use(page);
  },

  loginAs: async ({ page }, use) => {
    // Signature is (page, email, password) to match the AuthFixture type.
    // `page` from the closure is intentionally ignored so callers can pass
    // their own page (e.g. in tests with multiple pages).
    const login = async (targetPage: Page, email: string, password: string) => {
      await targetPage.goto('/auth/login');
      await targetPage.locator('input[name="email"]').fill(email);
      await targetPage.locator('input[name="password"]').fill(password);
      await targetPage.locator('button:has-text("Se connecter")').click();
      
      // Attendre que la connexion soit complète
      await targetPage.waitForLoadState('networkidle');
    };
    
    await use(login);
  },

  loginAsAdmin: async ({ loginAs }, use) => {
    const loginAdmin = async (page: Page) => {
      await loginAs(page, 'admin@test.local', 'Password123!');
      // URL after admin login: /{tenantSlug}/admin
      await page.waitForURL(/\/[^/]+\/admin$/);
    };
    
    await use(loginAdmin);
  },

  loginAsTeacher: async ({ loginAs }, use) => {
    const loginTeacher = async (page: Page) => {
      await loginAs(page, 'teacher@test.local', 'Password123!');
      // URL after teacher login: /{tenantSlug}/teacher
      await page.waitForURL(/\/[^/]+\/teacher$/);
    };
    
    await use(loginTeacher);
  },

  loginAsParent: async ({ loginAs }, use) => {
    const loginParent = async (page: Page) => {
      await loginAs(page, 'parent@test.local', 'Password123!');
      // URL after parent login: /{tenantSlug}/parent
      await page.waitForURL(/\/[^/]+\/parent$/);
    };
    
    await use(loginParent);
  },

  loginAsStudent: async ({ loginAs }, use) => {
    const loginStudent = async (page: Page) => {
      await loginAs(page, 'student@test.local', 'Password123!');
      // URL after student login: /{tenantSlug}/student
      await page.waitForURL(/\/[^/]+\/student$/);
    };
    
    await use(loginStudent);
  },
});

export { expect } from '@playwright/test';
