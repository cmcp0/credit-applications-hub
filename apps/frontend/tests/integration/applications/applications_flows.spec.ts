import { createPinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import CustomerApplicationsPage from "@/features/applications/views/customer_applications_page.vue";
import OperationApplicationsPage from "@/features/applications/views/operation_applications_page.vue";
import { useApplicationsStore } from "@/features/applications/store/applications_store";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { makeJwt, makeLoginResponse } from "../../helpers/auth_fixtures";

const Placeholder = { template: "<div>placeholder</div>" };

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", component: Placeholder },
      { path: "/forbidden", component: Placeholder },
      { path: "/applications/customer", component: CustomerApplicationsPage },
      { path: "/applications/operation", component: OperationApplicationsPage },
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

describe("applications feature flows", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("customer can create, list, and open application detail", async () => {
    const listItems: Array<Record<string, unknown>> = [
      {
        id: "app-1",
        country: "MX",
        status_code: "PENDING_REVIEW",
        requested_amount: 5000,
        created_at: "2026-02-17T00:00:00Z",
        updated_at: "2026-02-17T00:00:00Z",
      },
    ];

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = requestPath(input);
      const method = init?.method ?? "GET";

      if (path.includes("/api/applications") && method === "GET" && !path.includes("/api/applications/")) {
        return jsonResponse({
          items: listItems,
          page: 1,
          page_size: 20,
          total: listItems.length,
        });
      }

      if (path.endsWith("/api/applications") && method === "POST") {
        const body = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
        const created = {
          id: "app-2",
          country: body.country ?? "MX",
          status_code: "PENDING_REVIEW",
          requested_amount: body.requested_amount ?? 4000,
          created_at: "2026-02-17T00:05:00Z",
          updated_at: "2026-02-17T00:05:00Z",
        };
        listItems.unshift(created);
        return jsonResponse({
          id: created.id,
          country: created.country,
          status_code: created.status_code,
          created_at: created.created_at,
        }, 201);
      }

      if (path.includes("/api/applications/app-2") && method === "GET") {
        return jsonResponse({
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
        });
      }

      return jsonResponse({ code: "NOT_FOUND", message: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["customer"],
          permissions: ["applications:list_own", "applications:create"],
        }),
      }),
    );
    const router = buildRouter();
    await router.push("/applications/customer");
    await router.isReady();

    const wrapper = mount(CustomerApplicationsPage, {
      global: {
        plugins: [pinia, router],
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("app-1");

    await wrapper.find('input[placeholder="Jane Doe"]').setValue("Jane Doe");
    await wrapper.find('input[placeholder="ABC123456"]').setValue("ABC123456");
    await wrapper.find('input[placeholder="5000"]').setValue("4000");
    await wrapper.find('input[placeholder="2500"]').setValue("2000");
    await wrapper.find('form').trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("app-2");

    const openButtons = wrapper.findAll("button").filter((button) => button.text().trim() === "Open");
    await openButtons[0].trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Application Detail");
    expect(wrapper.text()).toContain("app-2");
  });

  it("operation surfaces actionable VERSION_CONFLICT guidance", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = requestPath(input);
      const method = init?.method ?? "GET";

      if (path.includes("/api/applications") && method === "GET" && !path.includes("/api/applications/")) {
        return jsonResponse({
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
        });
      }

      if (path.includes("/api/applications/app-1") && method === "GET") {
        return jsonResponse({
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
        });
      }

      if (path.includes("/api/applications/app-1/status") && method === "PATCH") {
        return jsonResponse(
          {
            code: "VERSION_CONFLICT",
            message: "Version conflict",
          },
          409,
        );
      }

      return jsonResponse({ code: "NOT_FOUND", message: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["operation"],
          permissions: ["applications:list_all", "applications:update_customer"],
        }),
      }),
    );
    const router = buildRouter();
    await router.push("/applications/operation");
    await router.isReady();

    const wrapper = mount(OperationApplicationsPage, {
      global: {
        plugins: [pinia, router],
      },
    });
    await flushPromises();

    const updateButtons = wrapper
      .findAll("button")
      .filter((button) => button.text().trim() === "Update Status");
    await updateButtons[0].trigger("click");
    await flushPromises();

    const applicationsStore = useApplicationsStore(pinia);
    await applicationsStore.updateForOperation("app-1", {
      status: "APPROVED",
      reason_code: "MANUAL_REVIEW_COMPLETED",
      expected_version: 2,
    });
    await flushPromises();

    expect(applicationsStore.errorMessage).toContain("updated by another process");
  });
});
