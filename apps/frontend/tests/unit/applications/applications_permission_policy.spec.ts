import { describe, expect, it } from "vitest";

import type { AuthPrincipal } from "@/features/auth/model/auth_types";
import {
  canAccessApplicationsModule,
  canCreateApplication,
  canUpdateApplicationStatus,
  resolveApplicationsTarget,
} from "@/features/applications/services/applications_permission_policy";

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

describe("applications_permission_policy", () => {
  it("allows customer module access with list_own permission", () => {
    expect(canAccessApplicationsModule("customer", ["applications:list_own"])).toBe(true);
  });

  it("denies admin module access", () => {
    expect(canAccessApplicationsModule("admin", ["users:manage_operations"])).toBe(false);
  });

  it("allows customer create only with create permission", () => {
    expect(canCreateApplication("customer", ["applications:create"])).toBe(true);
    expect(canCreateApplication("customer", ["applications:list_own"])).toBe(false);
  });

  it("allows operation status updates only with update_customer permission", () => {
    expect(canUpdateApplicationStatus("operation", ["applications:update_customer"])).toBe(true);
    expect(canUpdateApplicationStatus("operation", ["applications:list_all"])).toBe(false);
  });

  it("resolves operation applications route before customer route", () => {
    const target = resolveApplicationsTarget(
      principal({
        roles: ["operation", "customer"],
        permissions: ["applications:list_all", "applications:list_own"],
      }),
    );

    expect(target).toBe("/applications/operation");
  });

  it("resolves forbidden for admin-only principal", () => {
    const target = resolveApplicationsTarget(
      principal({
        roles: ["admin"],
        permissions: ["users:manage_operations", "workflows:manage"],
      }),
    );

    expect(target).toBe("/forbidden");
  });

  it("resolves forbidden when admin is combined with operation role", () => {
    const target = resolveApplicationsTarget(
      principal({
        roles: ["admin", "operation"],
        permissions: ["users:manage_operations", "workflows:manage", "applications:list_all"],
      }),
    );

    expect(target).toBe("/forbidden");
  });
});
