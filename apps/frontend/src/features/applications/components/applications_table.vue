<template>
  <Card custom-class="border-border/80">
    <CardHeader class="flex-row items-center justify-between space-y-0">
      <div>
        <CardTitle>{{ title }}</CardTitle>
        <CardDescription>{{ description }}</CardDescription>
      </div>
      <Button size="sm" variant="ghost" @click="$emit('refresh')">Refresh</Button>
    </CardHeader>
    <CardContent>
      <p v-if="isLoading" class="text-sm text-muted-foreground">Loading applications...</p>
      <p v-else-if="items.length === 0" class="text-sm text-muted-foreground">{{ emptyMessage }}</p>

      <div v-else class="overflow-auto">
        <table class="w-full min-w-[720px] text-left text-sm">
          <thead>
            <tr class="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
              <th class="py-2 pr-3">ID</th>
              <th class="py-2 pr-3">Country</th>
              <th class="py-2 pr-3">Status</th>
              <th class="py-2 pr-3">Requested</th>
              <th class="py-2 pr-3">Updated</th>
              <th class="py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="application in items"
              :key="application.id"
              class="border-b border-border/50 align-top"
            >
              <td class="py-3 pr-3 font-mono text-xs">{{ application.id }}</td>
              <td class="py-3 pr-3">{{ application.country }}</td>
              <td class="py-3 pr-3">{{ application.status_code }}</td>
              <td class="py-3 pr-3">{{ formatCurrency(application.requested_amount) }}</td>
              <td class="py-3 pr-3">{{ formatDate(application.updated_at) }}</td>
              <td class="py-3 text-right">
                <div class="inline-flex gap-2">
                  <Button size="sm" variant="secondary" @click="$emit('open', application.id)">
                    Open
                  </Button>
                  <Button
                    v-if="showStatusAction"
                    size="sm"
                    @click="$emit('prepareStatusUpdate', application.id)"
                  >
                    Update Status
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4 flex items-center justify-between border-t border-border pt-4 text-sm">
        <p class="text-muted-foreground">
          Page {{ page }} of {{ totalPages }} ({{ total }} total)
        </p>
        <div class="inline-flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            :disabled="page <= 1 || isLoading"
            @click="$emit('previousPage')"
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="secondary"
            :disabled="page >= totalPages || isLoading"
            @click="$emit('nextPage')"
          >
            Next
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, toRefs } from "vue";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApplicationSummary } from "@/features/applications/model/application_types";

defineEmits<{
  open: [applicationId: string];
  prepareStatusUpdate: [applicationId: string];
  refresh: [];
  previousPage: [];
  nextPage: [];
}>();

const props = withDefaults(
  defineProps<{
    title: string;
    description: string;
    items: ApplicationSummary[];
    isLoading: boolean;
    emptyMessage: string;
    page?: number;
    pageSize?: number;
    total?: number;
    showStatusAction?: boolean;
  }>(),
  {
    page: 1,
    pageSize: 20,
    total: 0,
    showStatusAction: false,
  },
);

const totalPages = computed(() => {
  if (!props.pageSize || props.pageSize <= 0) {
    return 1;
  }
  return Math.max(1, Math.ceil(props.total / props.pageSize));
});
const {
  title,
  description,
  items,
  isLoading,
  emptyMessage,
  page,
  total,
  showStatusAction,
} = toRefs(props);

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}
</script>
