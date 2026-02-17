<template>
  <DashboardShell
    role-label="Customer"
    title="Customer Dashboard"
    description="Track your applications and status changes."
  >
    <div class="flex flex-col gap-3">
      <p>Customer view is scoped to your own applications.</p>
      <RouterLink to="/applications/customer">
        <Button>Open My Applications</Button>
      </RouterLink>
    </div>
  </DashboardShell>
</template>

<script setup lang="ts">
import { RouterLink } from "vue-router";

import { Button } from "@/components/ui/button";
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";
</script>
