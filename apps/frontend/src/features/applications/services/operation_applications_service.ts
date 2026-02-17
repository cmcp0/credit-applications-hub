import {
  getApplication,
  listApplications,
  updateApplicationStatus,
} from "@/features/applications/api/applications_api";
import type {
  ApplicationDetail,
  ApplicationStatusUpdateResponse,
  ListApplicationsParams,
  ListApplicationsResponse,
  UpdateApplicationStatusRequest,
} from "@/features/applications/model/application_types";

export interface OperationApplicationsService {
  listApplications(params?: ListApplicationsParams): Promise<ListApplicationsResponse>;
  getApplication(applicationId: string): Promise<ApplicationDetail>;
  updateApplicationStatus(
    applicationId: string,
    input: UpdateApplicationStatusRequest,
  ): Promise<ApplicationStatusUpdateResponse>;
}

const operationApplicationsService: OperationApplicationsService = {
  listApplications(params: ListApplicationsParams = {}): Promise<ListApplicationsResponse> {
    return listApplications(params);
  },
  getApplication(applicationId: string): Promise<ApplicationDetail> {
    return getApplication(applicationId);
  },
  updateApplicationStatus(
    applicationId: string,
    input: UpdateApplicationStatusRequest,
  ): Promise<ApplicationStatusUpdateResponse> {
    return updateApplicationStatus(applicationId, input);
  },
};

export function createOperationApplicationsService(): OperationApplicationsService {
  return operationApplicationsService;
}
