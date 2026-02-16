import { createPinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/features/auth/views/login_page.vue";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { makeJwt } from "../../helpers/auth_fixtures";

const DashboardPlaceholder = { template: "<div>dashboard</div>" };
const ForbiddenPlaceholder = { template: "<div>forbidden</div>" };

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", component: LoginPage },
      { path: "/dashboard/customer", component: DashboardPlaceholder },
      { path: "/dashboard/operation", component: DashboardPlaceholder },
      { path: "/dashboard/admin", component: DashboardPlaceholder },
      { path: "/forbidden", component: ForbiddenPlaceholder },
    ],
  });
}

async function mountLoginPage() {
  const pinia = createPinia();
  const router = buildRouter();
  await router.push("/login");
  await router.isReady();

  const wrapper = mount(LoginPage, {
    global: {
      plugins: [pinia, router],
    },
  });

  const authStore = useAuthStore(pinia);

  return {
    wrapper,
    router,
    authStore,
  };
}

describe("login page flows", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("redirects to role dashboard on successful login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            access_token: makeJwt({
              roles: ["admin", "operation"],
              permissions: ["users:manage_operations", "applications:list_all"],
            }),
            token_type: "bearer",
            expires_in: 3600,
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      ),
    );

    const { wrapper, router } = await mountLoginPage();

    await wrapper.find('input[name="email"]').setValue("admin@example.com");
    await wrapper.find('input[name="password"]').setValue("password");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/dashboard/admin");
  });

  it("shows inline USER_INACTIVE error and stays on /login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "USER_INACTIVE",
            message: "User is inactive",
          }),
          {
            status: 403,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      ),
    );

    const { wrapper, router, authStore } = await mountLoginPage();

    await wrapper.find('input[name="email"]').setValue("inactive@example.com");
    await wrapper.find('input[name="password"]').setValue("password");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Your account is inactive. Contact an administrator.");
    expect(router.currentRoute.value.path).toBe("/login");
    expect(authStore.session).toBeNull();
  });

  it("shows throttling guidance for RATE_LIMIT_EXCEEDED", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "RATE_LIMIT_EXCEEDED",
            message: "Too many requests",
          }),
          {
            status: 429,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      ),
    );

    const { wrapper, router } = await mountLoginPage();

    await wrapper.find('input[name="email"]').setValue("user@example.com");
    await wrapper.find('input[name="password"]').setValue("password");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Too many attempts. Please wait and retry in a moment.");
    expect(router.currentRoute.value.path).toBe("/login");
  });
});
