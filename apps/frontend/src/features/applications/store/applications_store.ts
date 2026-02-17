import { defineStore } from "pinia";

import { ApplicationsApiError } from "@/features/applications/api/applications_api";
import type {
  ApplicationCreateResponse,
  ApplicationDetail,
  ApplicationSummary,
  CreateApplicationRequest,
  ListApplicationsParams,
  UpdateApplicationStatusRequest,
  ValidationFieldError,
} from "@/features/applications/model/application_types";
import { createCustomerApplicationsService } from "@/features/applications/services/customer_applications_service";
import { createOperationApplicationsService } from "@/features/applications/services/operation_applications_service";
import { mapStatusUpdateConflictMessage } from "@/features/applications/services/status_update_error_mapper";

interface ApplicationsState {
  items: ApplicationSummary[];
  detailById: Record<string, ApplicationDetail>;
  latestVersionById: Record<string, number>;
  currentDetailId: string | null;
  page: number;
  pageSize: number;
  total: number;
  isListLoading: boolean;
  isDetailLoading: boolean;
  isMutating: boolean;
  isRealtimeDegraded: boolean;
  errorMessage: string | null;
  validationErrors: ValidationFieldError[];
}

const customerService = createCustomerApplicationsService();
const operationService = createOperationApplicationsService();

export const useApplicationsStore = defineStore("applications_store", {
  state: (): ApplicationsState => ({
    items: [],
    detailById: {},
    latestVersionById: {},
    currentDetailId: null,
    page: 1,
    pageSize: 20,
    total: 0,
    isListLoading: false,
    isDetailLoading: false,
    isMutating: false,
    isRealtimeDegraded: false,
    errorMessage: null,
    validationErrors: [],
  }),
  getters: {
    currentDetail(state): ApplicationDetail | null {
      if (!state.currentDetailId) {
        return null;
      }
      return state.detailById[state.currentDetailId] ?? null;
    },
  },
  actions: {
    clearError(): void {
      this.errorMessage = null;
      this.validationErrors = [];
    },

    async loadCustomerList(params: ListApplicationsParams = {}): Promise<void> {
      this.clearError();
      this.isListLoading = true;

      try {
        const result = await customerService.listApplications(params);
        this.items = result.items;
        this.captureListVersions(result.items);
        this.page = result.page;
        this.pageSize = result.page_size;
        this.total = result.total;
      } catch (error) {
        this.setApiError(error, "Unable to load applications.");
      } finally {
        this.isListLoading = false;
      }
    },

    async loadOperationList(params: ListApplicationsParams = {}): Promise<void> {
      this.clearError();
      this.isListLoading = true;

      try {
        const result = await operationService.listApplications(params);
        this.items = result.items;
        this.captureListVersions(result.items);
        this.page = result.page;
        this.pageSize = result.page_size;
        this.total = result.total;
      } catch (error) {
        this.setApiError(error, "Unable to load operations queue.");
      } finally {
        this.isListLoading = false;
      }
    },

    async loadCustomerDetail(applicationId: string): Promise<void> {
      this.clearError();
      this.isDetailLoading = true;

      try {
        const detail = await customerService.getApplication(applicationId);
        this.detailById[applicationId] = detail;
        this.latestVersionById[applicationId] = detail.version;
        this.currentDetailId = applicationId;
      } catch (error) {
        this.setApiError(error, "Unable to load application details.");
      } finally {
        this.isDetailLoading = false;
      }
    },

    async loadOperationDetail(applicationId: string): Promise<void> {
      this.clearError();
      this.isDetailLoading = true;

      try {
        const detail = await operationService.getApplication(applicationId);
        this.detailById[applicationId] = detail;
        this.latestVersionById[applicationId] = detail.version;
        this.currentDetailId = applicationId;
      } catch (error) {
        this.setApiError(error, "Unable to load operation detail.");
      } finally {
        this.isDetailLoading = false;
      }
    },

    async createForCustomer(
      payload: CreateApplicationRequest,
    ): Promise<ApplicationCreateResponse | null> {
      this.clearError();
      this.isMutating = true;

      try {
        const created = await customerService.createApplication(payload);
        this.items = [
          {
            id: created.id,
            country: created.country,
            status_code: created.status_code,
            requested_amount: payload.requested_amount,
            created_at: created.created_at,
            updated_at: created.created_at,
          },
          ...this.items,
        ];
        this.total += 1;
        return created;
      } catch (error) {
        this.setApiError(error, "Unable to create application.");
        return null;
      } finally {
        this.isMutating = false;
      }
    },

    async updateForOperation(
      applicationId: string,
      payload: UpdateApplicationStatusRequest,
    ): Promise<boolean> {
      this.clearError();
      this.isMutating = true;

      try {
        const updated = await operationService.updateApplicationStatus(applicationId, payload);
        this.items = this.items.map((item) =>
          item.id === applicationId
            ? {
                ...item,
                status_code: updated.status_code,
                updated_at: updated.updated_at,
                version: updated.version,
              }
            : item,
        );
        this.latestVersionById[applicationId] = updated.version;
        const detail = await operationService.getApplication(applicationId);
        this.detailById[applicationId] = detail;
        this.latestVersionById[applicationId] = detail.version;
        this.currentDetailId = applicationId;
        return true;
      } catch (error) {
        if (error instanceof ApplicationsApiError) {
          const mappedConflictMessage = mapStatusUpdateConflictMessage(error);
          if (mappedConflictMessage) {
            this.errorMessage = mappedConflictMessage;
            this.validationErrors = [];
            await this.refreshOperationDetailSilently(applicationId);
            return false;
          }
        }

        this.setApiError(error, "Unable to update application status.");
        return false;
      } finally {
        this.isMutating = false;
      }
    },

    applyRealtimeSummary(summary: ApplicationSummary, version: number): void {
      const latestVersion = this.latestVersionById[summary.id];
      if (typeof latestVersion === "number" && version <= latestVersion) {
        return;
      }

      this.latestVersionById[summary.id] = version;

      const existingIndex = this.items.findIndex((item) => item.id === summary.id);
      if (existingIndex >= 0) {
        const items = [...this.items];
        items[existingIndex] = {
          ...summary,
          version,
        };
        this.items = items;
        return;
      }

      this.items = [
        {
          ...summary,
          version,
        },
        ...this.items,
      ];
      this.total += 1;
    },

    setRealtimeDegraded(value: boolean): void {
      this.isRealtimeDegraded = value;
    },

    setApiError(error: unknown, fallback: string): void {
      if (error instanceof ApplicationsApiError) {
        this.errorMessage = error.message;
        this.validationErrors = error.validationErrors;
        return;
      }

      this.errorMessage = fallback;
      this.validationErrors = [];
    },

    async refreshOperationDetailSilently(applicationId: string): Promise<void> {
      try {
        const detail = await operationService.getApplication(applicationId);
        this.detailById[applicationId] = detail;
        this.latestVersionById[applicationId] = detail.version;
        this.currentDetailId = applicationId;
        this.items = this.items.map((item) =>
          item.id === applicationId
            ? {
                ...item,
                status_code: detail.status_code,
                updated_at: detail.updated_at,
                version: detail.version,
              }
            : item,
        );
      } catch {
        // Keep existing state if detail refresh fails after a conflict.
      }
    },

    captureListVersions(items: ApplicationSummary[]): void {
      for (const item of items) {
        if (typeof item.version !== "number") {
          continue;
        }
        const latest = this.latestVersionById[item.id];
        if (typeof latest === "number" && latest >= item.version) {
          continue;
        }
        this.latestVersionById[item.id] = item.version;
      }
    },
  },
});
