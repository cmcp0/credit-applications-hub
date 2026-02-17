import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

test.describe("applications flows", () => {
  test("customer can create and open application detail", async ({ page }) => {
    await mockLogin(page, {
      roles: ["customer"],
      permissions: ["applications:list_own", "applications:create"],
    });
    await mockCustomerApplicationsApi(page);

    await page.goto("/login");
    await submitLogin(page, "customer@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/customer$/);

    await page.getByRole("button", { name: "Open My Applications" }).click();
    await expect(page).toHaveURL(/\/applications\/customer$/);

    await page.getByPlaceholder("Jane Doe").fill("Jane Doe");
    await page.getByPlaceholder("ABC123456").fill("ABC123456");
    await page.getByPlaceholder("5000").fill("4000");
    await page.getByPlaceholder("2500").fill("2000");
    await page.getByRole("button", { name: "Create application" }).click();

    await expect(page.getByText("app-2")).toBeVisible();
    await page.getByRole("button", { name: "Open" }).first().click();
    await expect(page.getByText("Application Detail")).toBeVisible();
  });

  test("operation gets actionable VERSION_CONFLICT message", async ({ page }) => {
    await mockLogin(page, {
      roles: ["operation"],
      permissions: ["applications:list_all", "applications:update_customer"],
    });
    await mockOperationConflictApi(page);

    await page.goto("/login");
    await submitLogin(page, "operation@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/operation$/);

    await page.getByRole("button", { name: "Open Operations Queue" }).click();
    await expect(page).toHaveURL(/\/applications\/operation$/);

    await page.getByRole("button", { name: "Update Status" }).first().click();
    await page.getByPlaceholder("APPROVED").fill("APPROVED");
    await page.getByRole("button", { name: "Apply transition" }).click();

    await expect(page.getByRole("alert").last()).toContainText("updated by another process");
  });

  test("admin is blocked from applications routes", async ({ page }) => {
    await mockLogin(page, {
      roles: ["admin", "operation"],
      permissions: ["users:manage_operations", "workflows:manage", "applications:list_all"],
    });

    await page.goto("/login");
    await submitLogin(page, "admin@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/admin$/);

    await page.goto("/applications/operation");
    await expect(page).toHaveURL(/\/forbidden$/);
    await expect(page.getByText("Access denied")).toBeVisible();
  });

  test("operation queue reflects realtime status updates", async ({ page }) => {
    await mockLogin(page, {
      roles: ["operation"],
      permissions: ["applications:list_all", "applications:update_customer"],
    });
    await mockOperationConflictApi(page);

    await page.goto("/login");
    await submitLogin(page, "operation@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/operation$/);

    await page.getByRole("button", { name: "Open Operations Queue" }).click();
    await expect(page).toHaveURL(/\/applications\/operation$/);
    await expect(page.getByText("PENDING_REVIEW")).toBeVisible();

    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent("credit-applications:realtime", {
        detail: {
          version: 3,
          application: {
            id: "app-1",
            country: "MX",
            status_code: "APPROVED",
            requested_amount: 5000,
            created_at: "2026-02-17T00:00:00Z",
            updated_at: "2026-02-17T00:01:00Z",
            version: 3,
          },
        },
      }));
    });

    await expect(page.getByText("APPROVED")).toBeVisible();
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

async function mockCustomerApplicationsApi(page: Page) {
  const items: Array<Record<string, unknown>> = [
    {
      id: "app-1",
      country: "MX",
      status_code: "PENDING_REVIEW",
      requested_amount: 5000,
      created_at: "2026-02-17T00:00:00Z",
      updated_at: "2026-02-17T00:00:00Z",
    },
  ];

  await page.route(/\/api\/applications(?:\/.*)?(?:\?.*)?$/, async (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());

    if (url.pathname === "/api/applications" && method === "GET") {
      await route.fulfill(jsonResponse({
        items,
        page: 1,
        page_size: 20,
        total: items.length,
      }));
      return;
    }

    if (url.pathname === "/api/applications" && method === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const created = {
        id: "app-2",
        country: payload.country ?? "MX",
        status_code: "PENDING_REVIEW",
        requested_amount: payload.requested_amount ?? 4000,
        created_at: "2026-02-17T00:05:00Z",
        updated_at: "2026-02-17T00:05:00Z",
      };
      items.unshift(created);
      await route.fulfill(
        jsonResponse(
          {
            id: created.id,
            country: created.country,
            status_code: created.status_code,
            created_at: created.created_at,
          },
          201,
        ),
      );
      return;
    }

    if (url.pathname === "/api/applications/app-2" && method === "GET") {
      await route.fulfill(
        jsonResponse({
          id: "app-2",
          country: "MX",
          status_code: "PENDING_REVIEW",
          requested_amount: 4000,
          created_at: "2026-02-17T00:05:00Z",
          updated_at: "2026-02-17T00:05:00Z",
          version: 1,
          status_metadata: {
            code: "PENDING_REVIEW",
            label: "Pending Review",
            is_terminal: false,
            allowed_transitions: ["APPROVED", "REJECTED"],
          },
        }),
      );
      return;
    }

    await route.fulfill(jsonResponse({ code: "NOT_FOUND", message: "Not found" }, 404));
  });
}

async function mockOperationConflictApi(page: Page) {
  await page.route(/\/api\/applications(?:\/.*)?(?:\?.*)?$/, async (route: Route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());

    if (url.pathname === "/api/applications" && method === "GET") {
      await route.fulfill(
        jsonResponse({
          items: [
            {
              id: "app-1",
              country: "MX",
              status_code: "PENDING_REVIEW",
              requested_amount: 5000,
              created_at: "2026-02-17T00:00:00Z",
              updated_at: "2026-02-17T00:00:00Z",
            },
          ],
          page: 1,
          page_size: 20,
          total: 1,
        }),
      );
      return;
    }

    if (url.pathname === "/api/applications/app-1" && method === "GET") {
      await route.fulfill(
        jsonResponse({
          id: "app-1",
          country: "MX",
          status_code: "PENDING_REVIEW",
          requested_amount: 5000,
          created_at: "2026-02-17T00:00:00Z",
          updated_at: "2026-02-17T00:00:00Z",
          version: 2,
          status_metadata: {
            code: "PENDING_REVIEW",
            label: "Pending Review",
            is_terminal: false,
            allowed_transitions: ["APPROVED", "REJECTED"],
          },
        }),
      );
      return;
    }

    if (url.pathname === "/api/applications/app-1/status" && method === "PATCH") {
      await route.fulfill(
        jsonResponse(
          {
            code: "VERSION_CONFLICT",
            message: "Version conflict",
          },
          409,
        ),
      );
      return;
    }

    await route.fulfill(jsonResponse({ code: "NOT_FOUND", message: "Not found" }, 404));
  });
}

function jsonResponse(body: unknown, status = 200) {
  return {
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  };
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
