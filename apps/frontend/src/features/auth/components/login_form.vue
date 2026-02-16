<template>
  <Card custom-class="w-full max-w-md border-border/80 bg-card/95 shadow-xl backdrop-blur">
    <CardHeader>
      <CardTitle>Sign in</CardTitle>
      <CardDescription>Enter your account credentials to continue.</CardDescription>
    </CardHeader>

    <CardContent>
      <form class="space-y-4" @submit.prevent="submitForm">
        <div class="space-y-2">
          <label class="text-sm font-medium" for="login-email">Email</label>
          <Input
            id="login-email"
            v-model="email"
            autocomplete="email"
            inputmode="email"
            name="email"
            placeholder="name@example.com"
            required
            type="email"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-medium" for="login-password">Password</label>
          <Input
            id="login-password"
            v-model="password"
            autocomplete="current-password"
            name="password"
            placeholder="Password"
            required
            type="password"
          />
        </div>

        <Alert v-if="localValidationMessage" variant="destructive">
          {{ localValidationMessage }}
        </Alert>

        <Alert v-else-if="errorMessage" variant="destructive">
          {{ errorMessage }}
        </Alert>

        <Button
          :aria-busy="isSubmitting"
          :disabled="isSubmitting"
          custom-class="w-full"
          type="submit"
        >
          {{ isSubmitting ? "Signing in..." : "Sign in" }}
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
import type { LoginRequest } from "@/features/auth/model/auth_types";

defineProps<{
  isSubmitting: boolean;
  errorMessage: string | null;
}>();

const emit = defineEmits<{
  submit: [payload: LoginRequest];
}>();

const email = ref("");
const password = ref("");
const localValidationMessage = ref<string | null>(null);

function submitForm(): void {
  const normalizedEmail = email.value.trim();
  if (!normalizedEmail || !password.value) {
    localValidationMessage.value = "Email and password are required.";
    return;
  }

  localValidationMessage.value = null;
  emit("submit", {
    email: normalizedEmail,
    password: password.value,
  });

  password.value = "";
}
</script>
