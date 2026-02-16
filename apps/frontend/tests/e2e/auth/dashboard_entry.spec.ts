import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

test.describe("role-based dashboard entry", () => {
  test("customer login lands on /dashboard/customer", async ({ page }) => {
    await mockLogin(page, {
      roles: ["customer"],
      permissions: ["applications:list_own"],
    });

    await page.goto("/login");
    await submitLogin(page, "customer@example.com", "password");

    await expect(page).toHaveURL(/\/dashboard\/customer$/);
  });

  test("operation login lands on /dashboard/operation", async ({ page }) => {
    await mockLogin(page, {
      roles: ["operation"],
      permissions: ["applications:list_all"],
    });

    await page.goto("/login");
    await submitLogin(page, "operation@example.com", "password");

    await expect(page).toHaveURL(/\/dashboard\/operation$/);
  });

  test("admin login lands on /dashboard/admin", async ({ page }) => {
    await mockLogin(page, {
      roles: ["admin", "operation"],
      permissions: ["users:manage_operations", "applications:list_all"],
    });

    await page.goto("/login");
    await submitLogin(page, "admin@example.com", "password");

    await expect(page).toHaveURL(/\/dashboard\/admin$/);
  });

  test("throttled login shows guidance and remains on /login", async ({ page }) => {
    await page.route("**/auth/login", async (route) => {
      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({
          code: "RATE_LIMIT_EXCEEDED",
          message: "Too many requests",
        }),
      });
    });

    await page.goto("/login");
    await submitLogin(page, "user@example.com", "password");

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("alert")).toContainText("Too many attempts. Please wait and retry in a moment.");
  });
});

async function submitLogin(page: Page, email: string, password: string) {
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

async function mockLogin(
  page: Page,
  options: {
    roles: string[];
    permissions: string[];
  },
) {
  await page.route("**/auth/login", async (route) => {
    const now = Math.floor(Date.now() / 1000);
    const token = makeJwt({
      sub: "user-1",
      roles: options.roles,
      permissions: options.permissions,
      iat: now,
      exp: now + 3600,
      iss: "credit-app-backend",
      aud: "credit-app-frontend",
    });

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: token,
        token_type: "bearer",
        expires_in: 3600,
      }),
    });
  });
}

function makeJwt(payload: Record<string, unknown>): string {
  const header = { alg: "HS256", typ: "JWT" };
  const encodedHeader = encodeBase64Url(header);
  const encodedPayload = encodeBase64Url(payload);
  return `${encodedHeader}.${encodedPayload}.signature`;
}

function encodeBase64Url(value: object): string {
  return Buffer.from(JSON.stringify(value), "utf-8")
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}
