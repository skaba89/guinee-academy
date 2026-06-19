/**
 * Guinée Academy — E2E Global Setup
 * Waits for all services to be ready before running tests.
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function waitForUrl(url: string, maxAttempts = 40, label = url): Promise<void> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(url);
      // Any HTTP response (even 5xx) means the server is alive and routing
      // requests. The /api/v1/health/ endpoint returns 503 when Redis is
      // unreachable, but the API is still fully functional for E2E tests.
      // We only fail on network errors (thrown by fetch).
      console.log(`  ✓ ${label} ready (HTTP ${res.status})`);
      return;
    } catch {
      // still starting — fetch threw, meaning no server is listening yet
    }
    await new Promise(r => setTimeout(r, 1500));
  }
  throw new Error(`${label} did not become ready after ${maxAttempts * 1.5}s`);
}

export default async () => {
  console.log('\n🧪 Guinée Academy — E2E environment setup\n');

  // ── 1. Check required Docker containers ──────────────────────────────────
  const REQUIRED = ['guinee-academy-postgres-1', 'guinee-academy-api-1'];
  try {
    const { stdout } = await execAsync('docker ps --format "{{.Names}}"');
    const running = stdout.split('\n');
    for (const name of REQUIRED) {
      if (!running.some(n => n.includes(name.replace('guinee-academy-', '')))) {
        console.warn(`  ⚠️  Container '${name}' not detected — tests may fail.`);
      }
    }
  } catch {
    console.warn('  ⚠️  Cannot check Docker containers (docker not in PATH?)');
  }

  // ── 2. Wait for API ───────────────────────────────────────────────────────
  // The backend runs Alembic migrations + operational DDL on first startup,
  // which can take 30-60s on a cold CI runner. Give it up to 180s.
  console.log('  ⏳ Waiting for API...');
  await waitForUrl('http://localhost:8000/api/v1/health/', 120, 'API (localhost:8000)');

  // ── 3. Wait for frontend (started by Playwright webServer) ───────────────
  console.log('  ⏳ Waiting for frontend dev server...');
  await waitForUrl('http://localhost:3000', 60, 'Frontend (localhost:3000)');

  console.log('\n✅ All services ready — starting tests!\n');
};
