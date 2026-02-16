<template>
  <div :class="cn(alertVariants({ variant }), customClass)" role="alert" v-bind="$attrs">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const alertVariants = cva("relative w-full rounded-lg border px-4 py-3 text-sm", {
  variants: {
    variant: {
      default: "bg-muted text-foreground border-border",
      destructive:
        "border-destructive/40 bg-destructive/10 text-destructive",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

type AlertVariants = VariantProps<typeof alertVariants>;

withDefaults(
  defineProps<{
    variant?: AlertVariants["variant"];
    customClass?: string;
  }>(),
  {
    variant: "default",
    customClass: "",
  },
);
</script>
