<template>
  <main class="mx-auto min-h-screen w-full max-w-6xl p-5">
    <Card custom-class="grid min-h-[calc(100vh-2.5rem)] gap-6 border-border/70 bg-card/95 p-6 shadow-sm">
      <header class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-secondary">
            {{ roleLabel }}
          </p>
          <h1 class="mt-1 text-3xl font-semibold tracking-tight">{{ title }}</h1>
          <p class="mt-2 max-w-3xl text-sm text-muted-foreground">{{ description }}</p>
        </div>
        <Button variant="ghost" @click="logout">Sign out</Button>
      </header>

      <section class="rounded-md border border-dashed border-border bg-muted p-4">
        <slot />
      </section>
    </Card>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAuthStore } from "@/features/auth/store/auth_store";

defineProps<{
  roleLabel: string;
  title: string;
  description: string;
}>();

const authStore = useAuthStore();
const router = useRouter();

async function logout(): Promise<void> {
  authStore.logout();
  await router.replace("/login");
}
</script>
