import { expect, test } from "@playwright/test";
import type { Page, Route } from "@playwright/test";

test.describe("admin workflow journeys", () => {
  test("admin manages operation users from dashboard journey", async ({ page }) => {
    await mockLogin(page, {
      roles: ["admin"],
      permissions: ["users:manage_operations"],
    });
    await mockOperationUsersApis(page);

    await page.goto("/login");
    await submitLogin(page, "admin@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/admin$/);

    await page.getByRole("button", { name: "Open Operation User Admin" }).click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/operation-users$/);
    await expect(page.getByText("ops1@example.com")).toBeVisible();

    await page.getByPlaceholder("User UUID").fill("new-user-1");
    await page.getByRole("button", { name: "Assign Role" }).click();
    await expect(page.getByText("new-user-1@example.com")).toBeVisible();
  });

  test("admin manages workflow catalog, graph editor, webhooks, and executions", async ({ page }) => {
    await mockLogin(page, {
      roles: ["admin"],
      permissions: ["workflows:manage"],
    });
    await mockWorkflowApis(page);

    await page.goto("/login");
    await submitLogin(page, "admin@example.com", "password");
    await expect(page).toHaveURL(/\/dashboard\/admin$/);

    await page.getByRole("button", { name: "Open Workflow Admin" }).click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows$/);
    await expect(page.getByRole("cell", { name: "wf-1" })).toBeVisible();

    await page.getByRole("button", { name: "Publish" }).first().click();
    await expect(page.getByRole("row", { name: /wf-1.*PUBLISHED/ })).toBeVisible();

    await page.getByRole("button", { name: "Editor" }).first().click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows\/wf-1\/editor$/);
    await page.getByRole("button", { name: "Save Graph" }).click();
    await expect(page.getByText("Workflow graph saved.")).toBeVisible();

    await page.getByRole("button", { name: "Back to Workflow Administration" }).click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows$/);

    await page.getByRole("button", { name: "Webhooks" }).first().click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows\/wf-1\/webhooks$/);
    await expect(page.getByRole("heading", { name: "Webhook Events" })).toBeVisible();

    await page.getByRole("button", { name: "Back to Workflow Administration" }).click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows$/);

    await page.getByRole("button", { name: "Executions" }).first().click();
    await expect(page).toHaveURL(/\/dashboard\/admin\/workflows\/wf-1\/executions$/);
    await expect(page.getByText("Execution Diagnostics")).toBeVisible();
  });
});

async function submitLogin(page: Page, email: string, password: string) {
  if (page.url().includes("/dashboard/")) {
    return;
  }
  await expect(page.getByLabel("Email")).toBeVisible();
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
      sub: "admin-user-1",
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

async function mockOperationUsersApis(page: Page) {
  let users = [
    {
      user_id: "op-user-1",
      email: "ops1@example.com",
      is_active: true,
      has_operation_role: true,
      updated_at: "2026-02-17T00:00:00Z",
    },
  ];

  await page.route("**/api/users/operations**", async (route: Route) => {
    const request = route.request();
    const method = request.method();
    const url = request.url();

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: users,
          page: 1,
          page_size: 20,
          total: users.length,
        }),
      });
      return;
    }

    if (method === "POST" && url.endsWith("/api/users/operations")) {
      const body = request.postDataJSON() as { user_id: string };
      users = [
        ...users,
        {
          user_id: body.user_id,
          email: `${body.user_id}@example.com`,
          is_active: true,
          has_operation_role: true,
          updated_at: "2026-02-17T00:10:00Z",
        },
      ];
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: body.user_id,
          assigned_role: "operation",
          assigned_at: "2026-02-17T00:10:00Z",
        }),
      });
      return;
    }

    if (method === "PATCH") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "op-user-1",
          enabled: true,
          updated_at: "2026-02-17T00:12:00Z",
        }),
      });
      return;
    }

    await route.fulfill({ status: 404, body: "Not found" });
  });
}

async function mockWorkflowApis(page: Page) {
  let workflows = [
    {
      id: "wf-1",
      country: "MX",
      version: 2,
      version_status: "DRAFT",
      active: false,
      published_at: null,
    },
  ];

  await page.route(/\/api\/workflows(?:\/.*)?(?:\?.*)?$/, async (route: Route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (method === "GET" && path === "/api/workflows") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: workflows }),
      });
      return;
    }

    if (method === "POST" && path === "/api/workflows/wf-1/publish") {
      workflows = workflows.map((workflow) =>
        workflow.id === "wf-1"
          ? {
              ...workflow,
              version_status: "PUBLISHED",
              active: true,
              published_at: "2026-02-17T01:00:00Z",
            }
          : workflow,
      );
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflow_id: "wf-1",
          country: "MX",
          version: 2,
          version_status: "PUBLISHED",
          active: true,
          published_at: "2026-02-17T01:00:00Z",
        }),
      });
      return;
    }

    if (method === "PUT" && path === "/api/workflows/wf-1/graph") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflow_id: "wf-1",
          version: 2,
          graph_revision: 3,
          etag: 'W/"workflow:wf-1:v2:r3"',
          counts: {
            operations: 1,
            sub_operations: 1,
            triggers: 1,
          },
          updated_at: "2026-02-17T01:05:00Z",
        }),
      });
      return;
    }

    if (method === "GET" && path === "/api/workflows/wf-1/webhooks/events") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          page: 1,
          page_size: 20,
          total: 0,
          sort_by: "occurred_at",
          sort_dir: "desc",
        }),
      });
      return;
    }

    if (method === "GET" && path === "/api/workflows/wf-1/executions") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          page: 1,
          page_size: 20,
          total: 0,
          sort_by: "updated_at",
          sort_dir: "desc",
        }),
      });
      return;
    }

    await route.fulfill({ status: 404, body: "Not found" });
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
