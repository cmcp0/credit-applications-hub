import { defineStore } from "pinia";

interface AdminWorkflowsState {
  selectedWorkflowId: string | null;
  isPollingEnabled: boolean;
  pollingIntervalMs: number;
  replayCooldownUntilByEventId: Record<string, number>;
}

export const useAdminWorkflowsStore = defineStore("admin_workflows_store", {
  state: (): AdminWorkflowsState => ({
    selectedWorkflowId: null,
    isPollingEnabled: true,
    pollingIntervalMs: 10_000,
    replayCooldownUntilByEventId: {},
  }),
  actions: {
    setSelectedWorkflow(workflowId: string | null): void {
      this.selectedWorkflowId = workflowId;
    },

    setPollingEnabled(enabled: boolean): void {
      this.isPollingEnabled = enabled;
    },

    setPollingInterval(intervalMs: number): void {
      this.pollingIntervalMs = Math.max(2_000, Math.trunc(intervalMs));
    },

    setReplayCooldown(eventId: string, cooldownUntilEpochMs: number): void {
      this.replayCooldownUntilByEventId[eventId] = cooldownUntilEpochMs;
    },

    replayCooldownRemainingMs(eventId: string): number {
      const until = this.replayCooldownUntilByEventId[eventId];
      if (!until) {
        return 0;
      }
      const remaining = until - Date.now();
      if (remaining <= 0) {
        delete this.replayCooldownUntilByEventId[eventId];
        return 0;
      }
      return remaining;
    },
  },
});
