"use client";

import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { X } from "@phosphor-icons/react";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

function DialogOverlay({ className, ...props }: DialogPrimitive.Backdrop.Props) {
  return <DialogPrimitive.Backdrop data-slot="dialog-overlay" className={cn("fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity data-ending-style:opacity-0 data-starting-style:opacity-0", className)} {...props} />;
}

function DialogContent({ className, children, showCloseButton = true, ...props }: DialogPrimitive.Popup.Props & { showCloseButton?: boolean }) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Popup data-slot="dialog-content" className={cn("fixed inset-x-4 top-1/2 z-50 mx-auto grid max-w-md -translate-y-1/2 gap-4 rounded-lg border bg-popover p-6 text-popover-foreground shadow-xl outline-none transition data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0", className)} {...props}>
        {children}
        {showCloseButton && <DialogPrimitive.Close aria-label="Fechar" render={<Button variant="ghost" size="icon-sm" className="absolute top-4 right-4" />}><X aria-hidden="true" /></DialogPrimitive.Close>}
      </DialogPrimitive.Popup>
    </DialogPrimitive.Portal>
  );
}

function DialogHeader({ className, ...props }: ComponentProps<"div">) { return <div data-slot="dialog-header" className={cn("flex flex-col gap-2", className)} {...props} />; }
function DialogFooter({ className, ...props }: ComponentProps<"div">) { return <div data-slot="dialog-footer" className={cn("mt-2 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)} {...props} />; }
function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) { return <DialogPrimitive.Title data-slot="dialog-title" className={cn("text-lg font-semibold", className)} {...props} />; }
function DialogDescription({ className, ...props }: DialogPrimitive.Description.Props) { return <DialogPrimitive.Description data-slot="dialog-description" className={cn("text-sm leading-6 text-muted-foreground", className)} {...props} />; }

export { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger };
