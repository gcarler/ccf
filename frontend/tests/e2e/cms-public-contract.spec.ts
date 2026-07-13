import { expect, test } from "@playwright/test";

const PUBLIC_PATHS = ["/", "/nosotros", "/eventos", "/plataforma/cms/readiness"];

test.describe("CMS public contract", () => {
  for (const path of PUBLIC_PATHS) {
    test(`${path} renders without internal browser errors`, async ({ page, baseURL }) => {
      const internalFailures: string[] = [];
      const consoleErrors: string[] = [];
      const origin = new URL(baseURL || "http://localhost:4173").origin;

      page.on("console", (message) => {
        if (message.type() === "error") {
          consoleErrors.push(message.text());
        }
      });
      page.on("response", (response) => {
        const url = response.url();
        if (!url.startsWith(origin)) return;
        if (response.status() >= 400) {
          internalFailures.push(`${response.status()} ${url}`);
        }
      });

      const response = await page.goto(path, { waitUntil: "networkidle" });
      expect(response?.ok(), `${path} should return a successful document response`).toBe(true);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.locator("body")).not.toHaveText("");
      if ((await page.locator("main").count()) > 0) {
        await expect(page.locator("main:visible").first()).toBeVisible();
      }
      expect(internalFailures, `Internal failed requests on ${path}`).toEqual([]);
      expect(consoleErrors, `Console errors on ${path}`).toEqual([]);
    });
  }

  test("public CMS API endpoints stay reachable", async ({ request }) => {
    for (const endpoint of [
      "/api/system/health",
      "/api/cms/v2/public/sites/ccf/pages/home",
      "/api/cms/v2/public/sites/ccf/theme",
      "/api/cms/v2/public/sites/ccf/menus/main",
    ]) {
      const response = await request.get(endpoint);
      expect(response.ok(), `${endpoint} should respond with 2xx`).toBe(true);
    }
  });
});
