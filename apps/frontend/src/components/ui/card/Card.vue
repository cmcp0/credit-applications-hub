<template>
  <section
    :class="cn('rounded-lg border border-border bg-card text-card-foreground shadow-sm', customClass)"
    v-bind="$attrs"
  >
    <slot />
  </section>
</template>

<script setup lang="ts">
import { cn } from "@/lib/utils";

withDefaults(
  defineProps<{
    customClass?: string;
  }>(),
  {
    customClass: "",
  },
);
</script>
