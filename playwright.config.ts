import { defineConfig, devices } from '@playwright/test';

/**
 * Configuration de Playwright pour les tests E2E
 * 
 * Docs: https://playwright.dev/docs/intro
 */
export default defineConfig({
  globalSetup: './tests/e2e/global-setup.ts',
  globalTeardown: './tests/e2e/global-teardown.ts',
  testDir: './tests/e2e',
  /* Exécuter les tests un par un */
  fullyParallel: true,
  /* Arrêter au premier test échoué */
  forbidOnly: !!process.env.CI,
  /* Pas de retries sur CI tant que les tests E2E ne sont pas stables
   * (les utilisateurs de test admin@test.local etc. ne sont pas seedés
   * dans le DB CI — chaque test échoue, et avec retries=2 le run dure
   * >60 min. Une fois le seeding en place, remettre retries: 2). */
  retries: process.env.CI ? 0 : 0,
  /* Workers parallèles sur CI */
  workers: process.env.CI ? 1 : undefined,
  /* Timeout par test — 15s suffit pour la plupart des flows;
   * éviter les hangs de 30s sur les tests qui dépendent d'un user
   * non seedé. */
  timeout: process.env.CI ? 15000 : 30000,
  /* Reporter: json pour CI, html pour développement */
  reporter: 'html',
  /* Configuration commune pour tous les projets */
  use: {
    /* URL de base de l'application */
    baseURL: 'http://localhost:3000',
    /* Capturer les captures d'écran en cas d'erreur */
    screenshot: 'only-on-failure',
    /* Enregistrer les vidéos en cas d'erreur */
    video: 'retain-on-failure',
    /* Tracer pour le débogage */
    trace: 'on-first-retry',
  },

  /* Configuration pour différents navigateurs */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* Tests sur mobile */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* Serveur de développement.
   * En CI, le serveur est déjà démarré par le workflow (vite preview
   * sur le port 3000) — on réutilise l'instance existante au lieu d'en
   * lancer une nouvelle qui entrerait en conflit de port. */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});
