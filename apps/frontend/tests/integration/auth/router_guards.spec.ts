import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import { createAppRouter } from "@/app/router";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { makeJwt, makeLoginResponse } from "../../helpers/auth_fixtures";

describe("router guards", () => {
  it("redirects unauthenticated access to protected dashboard into /login", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    const router = createAppRouter(authStore);

    await router.push("/dashboard/customer");

    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("redirects authenticated users from /login to resolved dashboard", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["operation"],
          permissions: ["applications:list_all"],
        }),
      }),
    );

    const router = createAppRouter(authStore);
    await router.push("/login");

    expect(router.currentRoute.value.path).toBe("/dashboard/operation");
  });

  it("routes authenticated principal without permitted dashboard to /forbidden", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["admin", "operation", "customer"],
          permissions: ["applications:create"],
        }),
      }),
    );

    const router = createAppRouter(authStore);
    await router.push("/");

    expect(router.currentRoute.value.path).toBe("/forbidden");
  });

  it("redirects authenticated user lacking route permission to /forbidden", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["customer"],
          permissions: ["applications:list_own"],
        }),
      }),
    );

    const router = createAppRouter(authStore);
    await router.push("/dashboard/admin");

    expect(router.currentRoute.value.path).toBe("/forbidden");
  });

  it("allows admin workflow route with workflows:manage permission", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["admin"],
          permissions: ["workflows:manage"],
        }),
      }),
    );

    const router = createAppRouter(authStore);
    await router.push("/dashboard/admin/workflows");

    expect(router.currentRoute.value.path).toBe("/dashboard/admin/workflows");
  });

  it("blocks admin workflow route without required permission", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["admin"],
          permissions: ["users:manage_operations"],
        }),
      }),
    );

    const router = createAppRouter(authStore);
    await router.push("/dashboard/admin/workflows");

    expect(router.currentRoute.value.path).toBe("/forbidden");
  });
});
