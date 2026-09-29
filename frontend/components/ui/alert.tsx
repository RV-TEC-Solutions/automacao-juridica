import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

const alertVariants = cva("flex w-full items-start gap-2 rounded-md border p-4 text-sm", {
  variants: { variant: { default: "bg-card text-card-foreground", destructive: "border-destructive/20 bg-destructive/10 text-destructive", success: "border-success/20 bg-success-soft text-success", warning: "border-warning/20 bg-warning-soft text-warning" } },
  defaultVariants: { variant: "default" },
});

function Alert({ className, variant, ...props }: ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div data-slot="alert" role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

function AlertTitle({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="alert-title" className={cn("font-semibold", className)} {...props} />;
}

function AlertDescription({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="alert-description" className={cn("min-w-0 flex-1 text-current/80", className)} {...props} />;
}

function AlertAction({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="alert-action" className={cn("ml-auto flex shrink-0 justify-end", className)} {...props} />;
}

export { Alert, AlertAction, AlertDescription, AlertTitle };
