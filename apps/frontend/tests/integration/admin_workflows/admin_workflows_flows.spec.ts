import { createPinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import AdminOperationUsersPage from "@/features/admin_workflows/views/admin_operation_users_page.vue";
import AdminWorkflowsPage from "@/features/admin_workflows/views/admin_workflows_page.vue";

const Placeholder = { template: "<div>placeholder</div>" };

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", component: Placeholder },
      { path: "/dashboard/admin", component: Placeholder },
      {
        path: "/dashboard/admin/operation-users",
        component: AdminOperationUsersPage,
      },
      {
        path: "/dashboard/admin/workflows",
        component: AdminWorkflowsPage,
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/editor",
        component: Placeholder,
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/webhooks",
        component: Placeholder,
      },
      {
        path: "/dashboard/admin/workflows/:workflowId/executions",
        component: Placeholder,
      },
    ],
  });
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestPath(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

describe("admin workflow pages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("operation-users page lists users and performs assign action", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = requestPath(input);
      const method = init?.method ?? "GET";

      if (path.includes("/api/users/operations") && method === "GET") {
        return jsonResponse({
          items: [
            {
              user_id: "user-1",
              email: "ops1@example.com",
              is_active: true,
              has_operation_role: true,
              updated_at: "2026-02-17T00:00:00Z",
            },
          ],
          page: 1,
          page_size: 20,
          total: 1,
        });
      }

      if (path.endsWith("/api/users/operations") && method === "POST") {
        return jsonResponse(
          {
            user_id: "user-2",
            assigned_role: "operation",
            assigned_at: "2026-02-17T00:01:00Z",
          },
          201,
        );
      }

      return jsonResponse({ code: "NOT_FOUND", message: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const pinia = createPinia();
    const router = buildRouter();
    await router.push("/dashboard/admin/operation-users");
    await router.isReady();

    const wrapper = mount(AdminOperationUsersPage, {
      global: {
        plugins: [pinia, router],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("ops1@example.com");

    await wrapper.find('input[placeholder="User UUID"]').setValue("user-2");
    const assignButton = wrapper.findAll("button").find((button) => button.text().includes("Assign Role"));
    expect(assignButton).toBeTruthy();
    await assignButton!.trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/users/operations"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("workflow page lists drafts and triggers publish", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = requestPath(input);
      const method = init?.method ?? "GET";

      if (path.includes("/api/workflows") && method === "GET") {
        return jsonResponse({
          items: [
            {
              id: "wf-1",
              country: "MX",
              version: 2,
              version_status: "DRAFT",
              active: false,
              published_at: null,
            },
          ],
        });
      }

      if (path.includes("/api/workflows/wf-1/publish") && method === "POST") {
        return jsonResponse({
          workflow_id: "wf-1",
          country: "MX",
          version: 2,
          version_status: "PUBLISHED",
          active: true,
          published_at: "2026-02-17T01:00:00Z",
        });
      }

      return jsonResponse({ code: "NOT_FOUND", message: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const pinia = createPinia();
    const router = buildRouter();
    await router.push("/dashboard/admin/workflows");
    await router.isReady();

    const wrapper = mount(AdminWorkflowsPage, {
      global: {
        plugins: [pinia, router],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("wf-1");

    const publishButton = wrapper.findAll("button").find((button) => button.text().trim() === "Publish");
    expect(publishButton).toBeTruthy();
    await publishButton!.trigger("click");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/workflows/wf-1/publish"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});

