<template>
  <DashboardShell
    role-label="Admin"
    title="Admin Dashboard"
    description="Manage operation users and workflow configuration access."
  >
    <p>
      Admin tools are permission-gated and intentionally explicit. Applications
      services are handled by customer and operation roles only.
    </p>
  </DashboardShell>
</template>

<script setup lang="ts">
import DashboardShell from "@/features/dashboards/dashboard_shell.vue";
</script>
