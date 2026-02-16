<template>
  <div :class="cn('p-6 pt-0', customClass)" v-bind="$attrs">
    <slot />
  </div>
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
