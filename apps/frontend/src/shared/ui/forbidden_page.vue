<template>
  <main class="flex min-h-screen items-center justify-center px-4">
    <Card custom-class="w-full max-w-xl border-border/80 bg-card/95 p-2 shadow-sm">
      <CardHeader>
        <CardTitle>Access denied</CardTitle>
        <CardDescription>
          You are authenticated but do not have permission for this route.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button v-if="isAuthenticated && principal" @click="goToDashboard">Go to dashboard</Button>
        <Button v-else @click="goToLogin">Back to sign in</Button>
      </CardContent>
    </Card>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { resolveDashboardTarget } from "@/features/auth/services/role_redirect";
import { useAuthStore } from "@/features/auth/store/auth_store";

const router = useRouter();
const authStore = useAuthStore();

const isAuthenticated = computed(() => authStore.hasValidSession());
const principal = computed(() => authStore.principal);

async function goToDashboard(): Promise<void> {
  if (!principal.value) {
    await router.replace("/login");
    return;
  }

  await router.replace(resolveDashboardTarget(principal.value));
}

async function goToLogin(): Promise<void> {
  await router.replace("/login");
}
</script>
