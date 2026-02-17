import {
  createApplication,
  getApplication,
  listApplications,
} from "@/features/applications/api/applications_api";
import type {
  ApplicationCreateResponse,
  ApplicationDetail,
  CreateApplicationRequest,
  ListApplicationsParams,
  ListApplicationsResponse,
} from "@/features/applications/model/application_types";

export interface CustomerApplicationsService {
  createApplication(input: CreateApplicationRequest): Promise<ApplicationCreateResponse>;
  listApplications(params?: ListApplicationsParams): Promise<ListApplicationsResponse>;
  getApplication(applicationId: string): Promise<ApplicationDetail>;
}

const customerApplicationsService: CustomerApplicationsService = {
  createApplication(input: CreateApplicationRequest): Promise<ApplicationCreateResponse> {
    return createApplication(input);
  },
  listApplications(params: ListApplicationsParams = {}): Promise<ListApplicationsResponse> {
    return listApplications(params);
  },
  getApplication(applicationId: string): Promise<ApplicationDetail> {
    return getApplication(applicationId);
  },
};

export function createCustomerApplicationsService(): CustomerApplicationsService {
  return customerApplicationsService;
}
