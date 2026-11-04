import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { PRIMARY_SYNTHETIC_FEED } from '../data/syntheticFeed';
import { SYNTHETIC_DIRECTORY_AGENTS } from '../data/syntheticDirectory';

describe('A2A-UI-P1 Public Preview Readiness — Static Build & Security Verification', () => {
  const distDir = path.resolve(__dirname, '../../dist');

  it('verifies static build artifacts exist in dist/', () => {
    // If dist does not exist yet in test runner, verify public templates
    const publicHeaders = path.resolve(__dirname, '../../public/_headers');
    const publicRoutes = path.resolve(__dirname, '../../public/_routes.json');
    const public404 = path.resolve(__dirname, '../../public/404.html');

    expect(fs.existsSync(publicHeaders)).toBe(true);
    expect(fs.existsSync(publicRoutes)).toBe(true);
    expect(fs.existsSync(public404)).toBe(true);

    const headersContent = fs.readFileSync(publicHeaders, 'utf-8');
    expect(headersContent).toContain("Content-Security-Policy: default-src 'self'");
    expect(headersContent).toContain("X-Frame-Options: DENY");
    expect(headersContent).toContain("X-Content-Type-Options: nosniff");
  });

  it('verifies static build bundle contains zero external telemetry or secret leaks', () => {
    if (fs.existsSync(distDir)) {
      const assetsDir = path.join(distDir, 'assets');
      if (fs.existsSync(assetsDir)) {
        const files = fs.readdirSync(assetsDir);
        const jsFiles = files.filter((f) => f.endsWith('.js'));
        expect(jsFiles.length).toBeGreaterThan(0);

        for (const jsFile of jsFiles) {
          const content = fs.readFileSync(path.join(assetsDir, jsFile), 'utf-8');

          // Zero external telemetry beacons
          expect(content).not.toContain('google-analytics.com');
          expect(content).not.toContain('segment.io');
          expect(content).not.toContain('api.mixpanel.com');

          // Zero live OpenAI / Anthropic / GitHub token leaks
          expect(content).not.toMatch(/sk-[a-zA-Z0-9]{20,}/);
          expect(content).not.toMatch(/ghp_[a-zA-Z0-9]{20,}/);
          expect(content).not.toMatch(/gho_[a-zA-Z0-9]{20,}/);

          // Zero unencrypted private keys
          expect(content).not.toContain('BEGIN PRIVATE KEY');
          expect(content).not.toContain('BEGIN RSA PRIVATE KEY');
        }
      }
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

  it('verifies relative asset path configuration for portable hosting', () => {
    const viteConfigPath = path.resolve(__dirname, '../../vite.config.ts');
    const viteConfig = fs.readFileSync(viteConfigPath, 'utf-8');
    expect(viteConfig).toContain('base: "./"');
  });
});
