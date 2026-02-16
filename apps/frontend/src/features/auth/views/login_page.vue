<template>
  <main class="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-6 px-5 py-8 lg:grid-cols-[1fr_420px]">
    <section
      class="rounded-lg border border-border/80 bg-gradient-to-br from-primary/10 via-card to-muted p-8 shadow-sm"
    >
      <h2 class="text-balance text-4xl font-semibold leading-tight text-foreground">
        Credit Applications Hub
      </h2>
      <p class="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
        Secure platform access
      </p>
      <p class="text-muted-foreground">
        Sign in to manage your credit applications, track progress, and access
        personalized insights. Our secure platform ensures your data is protected
        while providing you with the tools you need to succeed.
      </p>
    </section>

    <LoginForm
      :error-message="loginErrorMessage"
      :is-submitting="isSubmitting"
      @submit="handleSubmit"
    />
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import LoginForm from "@/features/auth/components/login_form.vue";
import { AuthApiError, login } from "@/features/auth/api/auth_api";
import type { LoginRequest } from "@/features/auth/model/auth_types";
import { resolveDashboardTarget } from "@/features/auth/services/role_redirect";
import { useAuthStore } from "@/features/auth/store/auth_store";

const router = useRouter();
const authStore = useAuthStore();

const isSubmitting = ref(false);
const loginErrorMessage = ref<string | null>(null);

async function handleSubmit(payload: LoginRequest): Promise<void> {
  loginErrorMessage.value = null;
  isSubmitting.value = true;

  try {
    const response = await login(payload);
    const session = authStore.applyLoginResponse(response);
    await router.replace(resolveDashboardTarget(session.principal));
  } catch (error) {
    loginErrorMessage.value = mapLoginError(error);
  } finally {
    isSubmitting.value = false;
  }
}

function mapLoginError(error: unknown): string {
  if (error instanceof AuthApiError) {
    if (error.status === 401 && error.code === "INVALID_CREDENTIALS") {
      return "Invalid email or password.";
    }

    if (error.status === 403 && error.code === "USER_INACTIVE") {
      return "Your account is inactive. Contact an administrator.";
    }

    if (error.status === 429 && error.code === "RATE_LIMIT_EXCEEDED") {
      return "Too many attempts. Please wait and retry in a moment.";
    }
  }

  return "Sign-in failed. Please try again.";
}
</script>
