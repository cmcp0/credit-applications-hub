<template>
  <Card custom-class="border-border/80">
    <CardHeader>
      <CardTitle>Create Application</CardTitle>
      <CardDescription>Submit a new customer credit application.</CardDescription>
    </CardHeader>
    <CardContent>
      <form class="grid gap-4" @submit.prevent="submitForm">
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="space-y-2 text-sm font-medium">
            <span>Country</span>
            <Input v-model="country" maxlength="2" placeholder="MX" required />
          </label>
          <label class="space-y-2 text-sm font-medium">
            <span>Requested Amount</span>
            <Input v-model="requestedAmount" inputmode="decimal" placeholder="5000" required />
            <p v-if="fieldError('requested_amount')" class="text-xs text-destructive">
              {{ fieldError("requested_amount") }}
            </p>
          </label>
        </div>

        <label class="space-y-2 text-sm font-medium">
          <span>Full Name</span>
          <Input v-model="fullName" maxlength="120" placeholder="Jane Doe" required />
          <p v-if="fieldError('full_name')" class="text-xs text-destructive">
            {{ fieldError("full_name") }}
          </p>
        </label>

        <div class="grid gap-2 sm:grid-cols-2">
          <label class="space-y-2 text-sm font-medium">
            <span>Identity Document</span>
            <Input v-model="identityDocument" maxlength="64" placeholder="ABC123456" required />
            <p v-if="fieldError('identity_document')" class="text-xs text-destructive">
              {{ fieldError("identity_document") }}
            </p>
          </label>
          <label class="space-y-2 text-sm font-medium">
            <span>Monthly Income</span>
            <Input v-model="monthlyIncome" inputmode="decimal" placeholder="2500" required />
            <p v-if="fieldError('monthly_income')" class="text-xs text-destructive">
              {{ fieldError("monthly_income") }}
            </p>
          </label>
        </div>

        <Alert v-if="localValidationError" variant="destructive">
          {{ localValidationError }}
        </Alert>
        <Alert v-else-if="errorMessage" variant="destructive">
          {{ errorMessage }}
        </Alert>

        <Button :disabled="isSubmitting" :aria-busy="isSubmitting" type="submit">
          {{ isSubmitting ? "Submitting..." : "Create application" }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type {
  CreateApplicationRequest,
  ValidationFieldError,
} from "@/features/applications/model/application_types";

const props = defineProps<{
  isSubmitting: boolean;
  errorMessage: string | null;
  validationErrors: ValidationFieldError[];
}>();

const emit = defineEmits<{
  submit: [payload: CreateApplicationRequest];
}>();

const country = ref("MX");
const fullName = ref("");
const identityDocument = ref("");
const requestedAmount = ref("");
const monthlyIncome = ref("");
const localValidationError = ref<string | null>(null);

function submitForm(): void {
  localValidationError.value = null;

  const parsedRequestedAmount = Number(requestedAmount.value);
  const parsedMonthlyIncome = Number(monthlyIncome.value);
  if (!Number.isFinite(parsedRequestedAmount) || parsedRequestedAmount <= 0) {
    localValidationError.value = "Requested amount must be greater than 0.";
    return;
  }

  if (!Number.isFinite(parsedMonthlyIncome) || parsedMonthlyIncome <= 0) {
    localValidationError.value = "Monthly income must be greater than 0.";
    return;
  }

  emit("submit", {
    country: country.value,
    full_name: fullName.value,
    identity_document: identityDocument.value,
    requested_amount: parsedRequestedAmount,
    monthly_income: parsedMonthlyIncome,
  });
}

function fieldError(field: string): string | null {
  const error = props.validationErrors.find((item) => item.field === field);
  return error?.message ?? null;
}
</script>
