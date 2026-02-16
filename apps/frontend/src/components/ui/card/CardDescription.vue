<template>
  <p :class="cn('text-sm text-muted-foreground', customClass)" v-bind="$attrs">
    <slot />
  </p>
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
