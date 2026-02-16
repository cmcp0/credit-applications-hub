import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { installAuthAwareFetch } from "@/app/bootstrap/auth_bootstrap";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { makeJwt, makeLoginResponse } from "../../helpers/auth_fixtures";

const Placeholder = { template: "<div>ok</div>" };

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", component: Placeholder },
      { path: "/forbidden", component: Placeholder },
      { path: "/dashboard/customer", component: Placeholder },
    ],
  });
}

describe("auth-aware fetch", () => {
  const originalFetch = window.fetch;

  beforeEach(() => {
    delete (window as Window & { __creditAuthFetchInstalled__?: boolean }).__creditAuthFetchInstalled__;
  });

  afterEach(() => {
    window.fetch = originalFetch;
  });

  it("rejects locally expired session before protected API call", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({ exp: 50 }),
      }),
    );

    const router = buildRouter();
    await router.push("/dashboard/customer");
    await router.isReady();

    const nativeFetch = vi.fn();
    window.fetch = nativeFetch as unknown as typeof window.fetch;

    installAuthAwareFetch(authStore, router);

    await expect(fetch("/api/applications")).rejects.toThrow("LOCAL_SESSION_EXPIRED");
    expect(nativeFetch).not.toHaveBeenCalled();
    expect(router.currentRoute.value.path).toBe("/login");
    expect(authStore.session).toBeNull();
  });

  it("clears session and redirects to /login for TOKEN_EXPIRED API response", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt(),
      }),
    );

    const router = buildRouter();
    await router.push("/dashboard/customer");
    await router.isReady();

    const nativeFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "TOKEN_EXPIRED", message: "Token is expired" }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );
    window.fetch = nativeFetch as unknown as typeof window.fetch;

    installAuthAwareFetch(authStore, router);

    await fetch("/api/applications");

    expect(router.currentRoute.value.path).toBe("/login");
    expect(authStore.session).toBeNull();
  });

  it("routes protected API 403 to /forbidden while keeping session", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt(),
      }),
    );
    const sessionBefore = authStore.session;

    const router = buildRouter();
    await router.push("/dashboard/customer");
    await router.isReady();

    const nativeFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "PERMISSION_DENIED", message: "Permission denied" }), {
        status: 403,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );
    window.fetch = nativeFetch as unknown as typeof window.fetch;

    installAuthAwareFetch(authStore, router);

    await fetch("/api/applications");

    expect(router.currentRoute.value.path).toBe("/forbidden");
    expect(authStore.session).toEqual(sessionBefore);
  });
});
