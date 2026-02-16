<template>
  <footer :class="cn('flex items-center p-6 pt-0', customClass)" v-bind="$attrs">
    <slot />
  </footer>
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
