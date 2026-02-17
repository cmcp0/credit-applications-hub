import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import { createAppRouter } from "@/app/router";
import { useAuthStore } from "@/features/auth/store/auth_store";
import { makeJwt, makeLoginResponse } from "../../helpers/auth_fixtures";

describe("applications router guards", () => {
  it("allows customer to access customer applications route", async () => {
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

    await router.push("/applications/customer");

    expect(router.currentRoute.value.path).toBe("/applications/customer");
  });

  it("allows operation to access operation applications route", async () => {
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

    await router.push("/applications/operation");

    expect(router.currentRoute.value.path).toBe("/applications/operation");
  });

  it("denies admin access to applications routes", async () => {
    const pinia = createPinia();
    const authStore = useAuthStore(pinia);
    authStore.applyLoginResponse(
      makeLoginResponse({
        access_token: makeJwt({
          roles: ["admin", "operation"],
          permissions: ["users:manage_operations", "workflows:manage", "applications:list_all"],
        }),
      }),
    );
    const router = createAppRouter(authStore);

    await router.push("/applications/operation");

    expect(router.currentRoute.value.path).toBe("/forbidden");
  });
});
