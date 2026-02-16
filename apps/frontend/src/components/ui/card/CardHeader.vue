<template>
  <header :class="cn('flex flex-col space-y-1.5 p-6', customClass)" v-bind="$attrs">
    <slot />
  </header>
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
