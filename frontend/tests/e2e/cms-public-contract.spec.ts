import { expect, test } from "@playwright/test";

const PUBLIC_PATHS = [
  "/",
  "/nosotros",
  "/eventos",
  "/pastores",
  "/testimonios",
  "/cursos",
  "/sedes",
  "/boletin",
  "/predicas",
  "/plataforma/cms/readiness",
];

const PUBLIC_API_ENDPOINTS = [
  "/api/system/health",
  "/api/cms/v2/public/sites/ccf/pages/home",
  "/api/cms/v2/public/sites/ccf/pages/about",
  "/api/cms/v2/public/sites/ccf/pages/events",
  "/api/cms/v2/public/sites/ccf/pages/pastors",
  "/api/cms/v2/public/sites/ccf/pages/testimonials",
  "/api/cms/v2/public/sites/ccf/pages/courses",
  "/api/cms/v2/public/sites/ccf/pages/locations",
  "/api/cms/v2/public/sites/ccf/pages/newsletter",
  "/api/cms/v2/public/sites/ccf/pages/sermons",
  "/api/cms/v2/public/sites/ccf/pages/blog",
  "/api/cms/v2/public/sites/ccf/theme",
  "/api/cms/v2/public/sites/ccf/menus/main",
];

test.describe("CMS public contract", () => {
  for (const path of PUBLIC_PATHS) {
    test(`${path} renders without internal browser errors`, async ({ page, baseURL }) => {
      const internalFailures: string[] = [];
      const consoleErrors: string[] = [];
      const origin = new URL(baseURL || "http://localhost:4173").origin;

      page.on("console", (message) => {
        if (message.type() === "error") {
          const text = message.text();
          if (text.includes("Failed to load resource: the server responded with a status of 400")) return;
          consoleErrors.push(text);
        }
      });
      page.on("response", (response) => {
        const url = response.url();
        if (!url.startsWith(origin)) return;
        if (url.includes("/_next/static/")) return;
        if (response.status() >= 400) {
          internalFailures.push(`${response.status()} ${url}`);
        }
      });

      const response = await page.goto(path, { waitUntil: "networkidle" });
      expect(response?.ok(), `${path} should return a successful document response`).toBe(true);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.locator("body")).not.toHaveText("");
      if ((await page.locator("main").count()) > 0) {
        await expect(page.locator("main").first()).toBeAttached();
      }
      expect(internalFailures, `Internal failed requests on ${path}`).toEqual([]);
      expect(consoleErrors, `Console errors on ${path}`).toEqual([]);
    });
  }

  test("public CMS API endpoints stay reachable", async ({ request }) => {
    for (const endpoint of PUBLIC_API_ENDPOINTS) {
      const response = await request.get(endpoint);
      expect(response.ok(), `${endpoint} should respond with 2xx`).toBe(true);
    }
  });
});
