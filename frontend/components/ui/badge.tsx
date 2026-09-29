import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex h-6 w-fit items-center gap-2 rounded-md border px-2 text-xs font-semibold whitespace-nowrap", {
  variants: {
    variant: {
      default: "border-primary bg-primary text-primary-foreground",
      secondary: "border-border bg-secondary text-secondary-foreground",
      outline: "border-border bg-card text-muted-foreground",
      success: "border-success/20 bg-success-soft text-success",
      warning: "border-warning/20 bg-warning-soft text-warning",
      destructive: "border-destructive/20 bg-destructive/10 text-destructive",
    },
  },
  defaultVariants: { variant: "secondary" },
});

function Badge({ className, variant, ...props }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
