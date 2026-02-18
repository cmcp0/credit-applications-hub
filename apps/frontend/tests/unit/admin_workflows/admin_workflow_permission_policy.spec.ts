import { describe, expect, it } from "vitest";

import type { AuthPrincipal } from "@/features/auth/model/auth_types";
import {
  canManageOperationUsers,
  canManageWorkflows,
} from "@/features/admin_workflows/services/admin_workflow_permission_policy";

function principal(overrides: Partial<AuthPrincipal> = {}): AuthPrincipal {
  return {
    sub: "admin-user",
    roles: ["admin"],
    permissions: [],
    exp: Math.floor(Date.now() / 1000) + 3600,
    iss: "issuer",
    aud: "audience",
    ...overrides,
  };
}

describe("admin_workflow_permission_policy", () => {
  it("allows operation-user management only for admin with permission", () => {
    expect(
      canManageOperationUsers(
        principal({ permissions: ["users:manage_operations"] }),
      ),
    ).toBe(true);
    expect(canManageOperationUsers(principal({ permissions: [] }))).toBe(false);
    expect(
      canManageOperationUsers(
        principal({
          roles: ["operation"],
          permissions: ["users:manage_operations"],
        }),
      ),
    ).toBe(false);
  });

  it("allows workflow management only for admin with permission", () => {
    expect(
      canManageWorkflows(principal({ permissions: ["workflows:manage"] })),
    ).toBe(true);
    expect(canManageWorkflows(principal({ permissions: [] }))).toBe(false);
    expect(
      canManageWorkflows(
        principal({
          roles: ["customer"],
          permissions: ["workflows:manage"],
        }),
      ),
    ).toBe(false);
  });
});
