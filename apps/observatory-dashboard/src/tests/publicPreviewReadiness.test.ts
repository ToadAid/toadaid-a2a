import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { PRIMARY_SYNTHETIC_FEED } from '../data/syntheticFeed';
import { SYNTHETIC_DIRECTORY_AGENTS } from '../data/syntheticDirectory';

describe('A2A-UI-P1-R1 Public Preview Routing & Security Qualification', () => {
  const distDir = path.resolve(__dirname, '../../dist');

  it('fails closed if production build output directory dist/ is missing', () => {
    expect(
      fs.existsSync(distDir),
      'Production build directory dist/ must exist. Build must precede test execution.'
    ).toBe(true);
  });

  it('verifies complete production build artifact inventory in dist/', () => {
    const distIndex = path.join(distDir, 'index.html');
    const distHeaders = path.join(distDir, '_headers');
    const dist404 = path.join(distDir, '404.html');
    const distRoutes = path.join(distDir, '_routes.json');
    const distAssets = path.join(distDir, 'assets');

    expect(fs.existsSync(distIndex), 'dist/index.html must exist').toBe(true);
    expect(fs.existsSync(distHeaders), 'dist/_headers must exist').toBe(true);
    expect(fs.existsSync(dist404), 'dist/404.html must exist').toBe(true);
    // _routes.json was removed because it is for Cloudflare Functions routing, not static SPA routing
    expect(fs.existsSync(distRoutes), 'dist/_routes.json must NOT exist').toBe(false);

    expect(fs.existsSync(distAssets), 'dist/assets directory must exist').toBe(true);
    const assetFiles = fs.readdirSync(distAssets);
    expect(assetFiles.some((f) => f.startsWith('blue-toby-') && f.endsWith('.png'))).toBe(true);
    expect(assetFiles.some((f) => f.startsWith('index-') && f.endsWith('.js'))).toBe(true);
    expect(assetFiles.some((f) => f.startsWith('index-') && f.endsWith('.css'))).toBe(true);
  });

  it('verifies relative asset paths and metadata in dist/index.html', () => {
    const indexContent = fs.readFileSync(path.join(distDir, 'index.html'), 'utf-8');

    // Title & meta description
    expect(indexContent).toContain('ToadAid Agent Observatory — Public Preview');
    expect(indexContent).toContain('ToadAid Sovereign Agent-to-Agent (A2A) Telemetry and Seam Governance');

    // Relative asset references
    expect(indexContent).toContain('src="./assets/');
    expect(indexContent).toContain('href="./assets/');
    expect(indexContent).toContain('href="./favicon.svg"');
  });

  it('verifies hardened security headers in dist/_headers', () => {
    const headersContent = fs.readFileSync(path.join(distDir, '_headers'), 'utf-8');

    expect(headersContent).toContain("Content-Security-Policy: default-src 'self'");
    expect(headersContent).toContain("connect-src 'self'");
    expect(headersContent).toContain("frame-ancestors 'none'");
    expect(headersContent).toContain('X-Frame-Options: DENY');
    expect(headersContent).toContain('X-Content-Type-Options: nosniff');
    expect(headersContent).toContain('Referrer-Policy: strict-origin-when-cross-origin');
    expect(headersContent).toContain('Cache-Control: public, max-age=31536000, immutable');
  });

  it('verifies static 404 fallback page contains absolute return link to root and resolves from nested paths', () => {
    const fourOhFour = fs.readFileSync(path.join(distDir, '404.html'), 'utf-8');
    expect(fourOhFour).toContain('404 — Route Not Found');
    expect(fourOhFour).toContain('href="/"');

    // R2 qualification: Verify href="/" resolves strictly to root "/"
    // even when loaded from deeply nested nonexistent URLs (e.g. /missing/section/ or /dashboard/)
    const nestedTestUrls = [
      'https://agent.toadaid.org/missing/section/',
      'https://agent.toadaid.org/dashboard/',
      'https://agent.toadaid.org/deeply/nested/nonexistent/subpath/',
      'https://agent.toadaid.org/unmatched-route',
    ];

    const match = fourOhFour.match(/href="([^"]+)"/);
    expect(match).not.toBeNull();
    const hrefValue = match![1];
    expect(hrefValue).toBe('/');

    for (const nestedUrl of nestedTestUrls) {
      const resolved = new URL(hrefValue, nestedUrl);
      expect(resolved.pathname).toBe('/');
      expect(resolved.origin).toBe('https://agent.toadaid.org');
    }
  });

  it('performs deterministic bundle scanning for known telemetry beacons and credentials', () => {
    const assetsDir = path.join(distDir, 'assets');
    const files = fs.readdirSync(assetsDir);
    const jsFiles = files.filter((f) => f.endsWith('.js'));
    expect(jsFiles.length).toBeGreaterThan(0);

    for (const jsFile of jsFiles) {
      const content = fs.readFileSync(path.join(assetsDir, jsFile), 'utf-8');

      // Prohibited external telemetry domains
      expect(content).not.toContain('google-analytics.com');
      expect(content).not.toContain('segment.io');
      expect(content).not.toContain('api.mixpanel.com');

      // Prohibited live API base URLs
      expect(content).not.toContain('api.openai.com');
      expect(content).not.toContain('api.anthropic.com');

      // Prohibited credential / token patterns
      expect(content).not.toMatch(/sk-[a-zA-Z0-9]{20,}/);
      expect(content).not.toMatch(/ghp_[a-zA-Z0-9]{20,}/);
      expect(content).not.toMatch(/gho_[a-zA-Z0-9]{20,}/);
      expect(content).not.toContain('BEGIN PRIVATE KEY');
    }
  });

  it('enforces immutable false authority flags in primary synthetic feed', () => {
    const flags = PRIMARY_SYNTHETIC_FEED.authorityFlags;
    expect(flags.executionAuthorized).toBe(false);
    expect(flags.publicationAuthorized).toBe(false);
    expect(flags.deploymentAuthorized).toBe(false);
    expect(flags.agentRegistrationActive).toBe(false);
    expect(flags.publicDirectoryExposed).toBe(false);

    expect(PRIMARY_SYNTHETIC_FEED.status).toBe('SYNTHETIC_LOCAL_FOUNDATION_READ_ONLY');
    expect(PRIMARY_SYNTHETIC_FEED.kind).toBe('toadaid-observatory-owner-dashboard-feed');
  });

  it('enforces synthetic directory labeling and isolation', () => {
    expect(SYNTHETIC_DIRECTORY_AGENTS.length).toBeGreaterThan(0);
    for (const agent of SYNTHETIC_DIRECTORY_AGENTS) {
      expect(agent.agentRef).toMatch(/^agent-synthetic-/);
      expect(agent.tenantRef).toMatch(/^tenant-/);
      expect(agent.ownerRef).toMatch(/^owner-/);
    }
  });
});
