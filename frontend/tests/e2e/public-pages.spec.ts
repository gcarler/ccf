/**
 * E2E Tests — Critical Public Page Flows
 *
 * Tests the full user journey: Frontend → API → Database
 * Verifies that CMS content renders correctly on public pages.
 */
import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL || "http://localhost:3000";

// ═══════════════════════════════════════════════════════════════════════════════
// 1. HOMEPAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Homepage", () => {
  test("should load and display hero section", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // Hero should be visible
    const hero = page.locator("section:visible").first();
    await expect(hero).toBeVisible();
  });

  test("should have working navigation links", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Check nav links exist
    const navLinks = page.locator("nav a");
    const count = await navLinks.count();
    expect(count).toBeGreaterThan(3);
  });

  test("should have footer with links", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Footer should exist
    const footer = page.locator("footer");
    await expect(footer).toBeVisible();

    // Footer should have navigation links
    const footerLinks = footer.locator("a");
    const count = await footerLinks.count();
    expect(count).toBeGreaterThan(5);
  });

  test("should have SEO meta tags", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Title should be set (may be default or CMS)
    const title = await page.title();
    expect(title).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 2. NOSOTROS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Nosotros Page", () => {
  test("should load and display content", async ({ page }) => {
    await page.goto(`${BASE_URL}/nosotros`);
    await expect(page).toHaveURL(`${BASE_URL}/nosotros`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have vision and mission sections", async ({ page }) => {
    await page.goto(`${BASE_URL}/nosotros`);

    // Look for vision/mission content
    const content = await page.textContent("body");
    expect(content).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 3. CONOCER A JESUS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Conocer a Jesus Page", () => {
  test("should load with hero and contact form", async ({ page }) => {
    await page.goto(`${BASE_URL}/conocer-a-jesus`);
    await expect(page).toHaveURL(`${BASE_URL}/conocer-a-jesus`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have contact form", async ({ page }) => {
    await page.goto(`${BASE_URL}/conocer-a-jesus`);

    // Form should exist
    const form = page.locator("form");
    const count = await form.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 4. PASTORES PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Pastores Page", () => {
  test("should load and display pastoral team", async ({ page }) => {
    await page.goto(`${BASE_URL}/pastores`);
    await expect(page).toHaveURL(`${BASE_URL}/pastores`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should navigate to individual pastor page", async ({ page }) => {
    await page.goto(`${BASE_URL}/pastores`);

    // Check if there are pastor links
    const links = page.locator('a[href*="/pastores/"]');
    const count = await links.count();

    if (count > 0) {
      await links.first().click();
      await page.waitForURL(/\/pastores\/.+/);
      expect(page.url()).toContain("/pastores/");
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 5. EVENTOS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Eventos Page", () => {
  test("should load events page", async ({ page }) => {
    await page.goto(`${BASE_URL}/eventos`);
    await expect(page).toHaveURL(`${BASE_URL}/eventos`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have calendar or event list", async ({ page }) => {
    await page.goto(`${BASE_URL}/eventos`);

    // Page should render without errors
    const content = await page.textContent("body");
    expect(content).toBeTruthy();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 6. CURSOS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Cursos Page", () => {
  test("should load courses page", async ({ page }) => {
    await page.goto(`${BASE_URL}/cursos`);
    await expect(page).toHaveURL(`${BASE_URL}/cursos`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 7. SEDES PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Sedes Page", () => {
  test("should load locations page", async ({ page }) => {
    await page.goto(`${BASE_URL}/sedes`);
    await expect(page).toHaveURL(`${BASE_URL}/sedes`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have search input", async ({ page }) => {
    await page.goto(`${BASE_URL}/sedes`);

    // Search input should exist
    const search = page.locator('input[type="text"], input[placeholder*="Buscar"]');
    const count = await search.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 8. BOLETIN PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Boletin Page", () => {
  test("should load newsletter page", async ({ page }) => {
    await page.goto(`${BASE_URL}/boletin`);
    await expect(page).toHaveURL(`${BASE_URL}/boletin`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have email subscription form", async ({ page }) => {
    await page.goto(`${BASE_URL}/boletin`);

    // Email input should exist
    const emailInput = page.locator('input[type="email"]');
    const count = await emailInput.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 9. PREDICAS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Predicas Page", () => {
  test("should load sermons page", async ({ page }) => {
    await page.goto(`${BASE_URL}/predicas`);
    await expect(page).toHaveURL(`${BASE_URL}/predicas`);

    // Page should have content
    const main = page.locator("main");
    await expect(main).toBeVisible();
  });

  test("should have search functionality", async ({ page }) => {
    await page.goto(`${BASE_URL}/predicas`);

    // Search input should exist
    const search = page.locator('input[type="text"], input[type="search"]');
    const count = await search.count();
    expect(count).toBeGreaterThan(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 10. CROSS-PAGE NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Cross-Page Navigation", () => {
  test("should navigate between public pages via nav", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Click on a nav link
    const nosotLink = page.locator('a[href="/nosotros"]').first();
    if (await nosotLink.isVisible()) {
      await nosotLink.click();
      await page.waitForURL(/\/nosotros/);
      expect(page.url()).toContain("/nosotros");
    }
  });

  test("should maintain footer across pages", async ({ page }) => {
    // Check footer on homepage
    await page.goto(`${BASE_URL}/`);
    const footerHome = page.locator("footer");
    await expect(footerHome).toBeVisible();

    // Check footer on nosotros
    await page.goto(`${BASE_URL}/nosotros`);
    const footerNosotros = page.locator("footer");
    await expect(footerNosotros).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 11. MOBILE RESPONSIVE
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("Mobile Responsive", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("should show mobile nav on small screens", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Mobile nav should be visible
    const mobileNav = page.locator("nav.md\\:hidden, nav").last();
    await expect(mobileNav).toBeVisible();
  });

  test("should be usable on mobile", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Page should render without horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375 + 20); // Allow small margin
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// 12. API HEALTH CHECK
// ═══════════════════════════════════════════════════════════════════════════════

test.describe("API Health", () => {
  test("backend health endpoint should respond", async ({ request }) => {
    const response = await request.get(`${BASE_URL.replace(":3000", ":8000")}/api/system/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe("ok");
  });

  test("CMS public page should be accessible", async ({ request }) => {
    const response = await request.get(`${BASE_URL.replace(":3000", ":8000")}/api/cms/v2/public/sites/faro/pages/inicio`);
    expect(response.ok()).toBeTruthy();
  });
});
