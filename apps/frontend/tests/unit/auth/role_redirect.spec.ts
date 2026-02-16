import { describe, expect, it } from "vitest";

import type { AuthPrincipal } from "@/features/auth/model/auth_types";
import { canAccessDashboard, resolveDashboardTarget } from "@/features/auth/services/role_redirect";

function principal(overrides: Partial<AuthPrincipal> = {}): AuthPrincipal {
  return {
    sub: "user-1",
    roles: ["customer"],
    permissions: ["applications:list_own"],
    exp: Math.floor(Date.now() / 1000) + 3600,
    iss: "issuer",
    aud: "audience",
    ...overrides,
  };
}

describe("role_redirect", () => {
  it("routes admin first when admin permissions are present", () => {
    const target = resolveDashboardTarget(
      principal({
        roles: ["admin", "operation", "customer"],
        permissions: ["users:manage_operations", "applications:list_all", "applications:list_own"],
      }),
    );

    expect(target).toBe("/dashboard/admin");
  });

  it("falls back by priority when higher role lacks dashboard permission", () => {
    const target = resolveDashboardTarget(
      principal({
        roles: ["admin", "operation", "customer"],
        permissions: ["applications:list_all", "applications:list_own"],
      }),
    );

    expect(target).toBe("/dashboard/operation");
  });

  it("returns forbidden when no role has required permission", () => {
    const target = resolveDashboardTarget(
      principal({
        roles: ["admin", "operation", "customer"],
        permissions: ["applications:create"],
      }),
    );

    expect(target).toBe("/forbidden");
  });

  it("checks dashboard permission contracts", () => {
    expect(canAccessDashboard(["applications:list_own"], "/dashboard/customer")).toBe(true);
    expect(canAccessDashboard(["applications:list_all"], "/dashboard/operation")).toBe(true);
    expect(canAccessDashboard(["workflows:manage"], "/dashboard/admin")).toBe(true);
    expect(canAccessDashboard(["users:read"], "/dashboard/admin")).toBe(false);
  });
});
