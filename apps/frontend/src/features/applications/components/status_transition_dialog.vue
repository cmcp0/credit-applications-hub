<template>
  <Card custom-class="border-border/80">
    <CardHeader>
      <CardTitle>Status Transition</CardTitle>
      <CardDescription>
        Run a workflow status change for the selected application.
      </CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="submitForm">
        <div class="grid gap-2">
          <p class="text-sm text-muted-foreground">
            <span class="font-medium text-foreground">Application:</span>
            {{ applicationId ?? "Select an application first" }}
          </p>
          <p class="text-sm text-muted-foreground">
            <span class="font-medium text-foreground">Current status:</span>
            {{ currentStatusCode ?? "-" }}
          </p>
          <p class="text-sm text-muted-foreground">
            <span class="font-medium text-foreground">Expected version:</span>
            {{ expectedVersion ?? "-" }}
          </p>
        </div>

        <label class="space-y-2 text-sm font-medium">
          <span>Target Status</span>
          <Input v-model="targetStatus" maxlength="120" placeholder="APPROVED" required />
        </label>

        <label class="space-y-2 text-sm font-medium">
          <span>Reason Code</span>
          <Input
            v-model="reasonCode"
            maxlength="120"
            placeholder="MANUAL_REVIEW_COMPLETED"
          />
        </label>

        <Alert v-if="localValidationError" variant="destructive">
          {{ localValidationError }}
        </Alert>
        <Alert v-else-if="!props.canUpdateStatus" variant="destructive">
          Missing permission: <code>applications:update_customer</code>.
        </Alert>
        <Alert v-else-if="errorMessage" variant="destructive">
          {{ errorMessage }}
        </Alert>

        <Button
          :disabled="isSubmitting || !props.canUpdateStatus || !applicationId || expectedVersion === null"
          :aria-busy="isSubmitting"
          type="submit"
        >
          {{ isSubmitting ? "Updating..." : "Apply transition" }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const props = defineProps<{
  applicationId: string | null;
  currentStatusCode: string | null;
  expectedVersion: number | null;
  isSubmitting: boolean;
  canUpdateStatus: boolean;
  errorMessage: string | null;
}>();

const emit = defineEmits<{
  submit: [
    payload: {
      applicationId: string;
      status: string;
      reason_code?: string;
      expected_version: number;
    },
  ];
}>();

const targetStatus = ref("");
const reasonCode = ref("");
const localValidationError = ref<string | null>(null);

watch(
  () => props.currentStatusCode,
  (value) => {
    targetStatus.value = value ?? "";
  },
  { immediate: true },
);

function submitForm(): void {
  localValidationError.value = null;

  if (!props.canUpdateStatus) {
    localValidationError.value = "Missing permission to update application status.";
    return;
  }

  if (!props.applicationId) {
    localValidationError.value = "Select an application before updating status.";
    return;
  }

  if (props.expectedVersion === null) {
    localValidationError.value = "Expected version is required. Open application detail first.";
    return;
  }

  if (!targetStatus.value.trim()) {
    localValidationError.value = "Target status is required.";
    return;
  }

  emit("submit", {
    applicationId: props.applicationId,
    status: targetStatus.value,
    reason_code: reasonCode.value.trim() || undefined,
    expected_version: props.expectedVersion,
  });
}
</script>
