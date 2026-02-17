<template>
  <DashboardShell
    role-label="Operation"
    title="Operations Dashboard"
    description="Review queues and process status transitions."
  >
    <div class="flex flex-col gap-3">
      <p>
        Operation actions in this MVP are limited to customer application status transitions.
      </p>
      <RouterLink to="/applications/operation">
        <Button>Open Operations Queue</Button>
      </RouterLink>
    </div>
  </DashboardShell>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

import { Button } from "@/components/ui/button";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";
</script>
