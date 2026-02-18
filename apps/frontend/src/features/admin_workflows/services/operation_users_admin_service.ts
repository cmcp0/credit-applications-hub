import {
  assignOperationRole,
  listOperationUsers,
  setOperationAccess,
  type ListOperationUsersParams,
} from "@/features/admin_workflows/api/operation_users_api";
import type { OperationUsersListResponse } from "@/features/admin_workflows/model/admin_workflow_types";

export interface OperationUsersAdminService {
  listOperationUsers(params?: ListOperationUsersParams): Promise<OperationUsersListResponse>;
  assignOperationRole(input: { user_id: string }): Promise<{
    user_id: string;
    assigned_role: string;
    assigned_at: string;
  }>;
  setOperationAccess(
    userId: string,
    input: { enabled: boolean },
  ): Promise<{
    user_id: string;
    enabled: boolean;
    updated_at: string;
  }>;
}

export function createOperationUsersAdminService(): OperationUsersAdminService {
  return {
    listOperationUsers,
    assignOperationRole,
    setOperationAccess,
  };
}
