"use client";

import { Dialog as SheetPrimitive } from "@base-ui/react/dialog";
import { X } from "@phosphor-icons/react";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const Sheet = SheetPrimitive.Root;
const SheetTrigger = SheetPrimitive.Trigger;
const SheetClose = SheetPrimitive.Close;

function SheetContent({ className, children, showCloseButton = true, ...props }: SheetPrimitive.Popup.Props & { showCloseButton?: boolean }) {
  return (
    <SheetPrimitive.Portal>
      <SheetPrimitive.Backdrop className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm transition-opacity data-ending-style:opacity-0 data-starting-style:opacity-0" />
      <SheetPrimitive.Popup data-slot="sheet-content" className={cn("fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l bg-popover text-popover-foreground shadow-xl outline-none transition-transform data-ending-style:translate-x-full data-starting-style:translate-x-full", className)} {...props}>
        {children}
        {showCloseButton && <SheetPrimitive.Close aria-label="Fechar" render={<Button variant="ghost" size="icon-sm" className="absolute right-4 top-4 z-20" />}><X aria-hidden="true" /></SheetPrimitive.Close>}
      </SheetPrimitive.Popup>
    </SheetPrimitive.Portal>
  );
}

function SheetHeader({ className, ...props }: ComponentProps<"div">) { return <div data-slot="sheet-header" className={cn("flex flex-col gap-2 border-b p-6", className)} {...props} />; }
function SheetFooter({ className, ...props }: ComponentProps<"div">) { return <div data-slot="sheet-footer" className={cn("mt-auto flex gap-2 border-t p-6", className)} {...props} />; }
function SheetTitle({ className, ...props }: SheetPrimitive.Title.Props) { return <SheetPrimitive.Title data-slot="sheet-title" className={cn("text-lg font-semibold", className)} {...props} />; }
function SheetDescription({ className, ...props }: SheetPrimitive.Description.Props) { return <SheetPrimitive.Description data-slot="sheet-description" className={cn("text-sm text-muted-foreground", className)} {...props} />; }

export { Sheet, SheetClose, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger };
