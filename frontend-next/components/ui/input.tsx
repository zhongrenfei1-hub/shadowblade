import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-card/60 px-3 py-2 text-sm transition-colors placeholder:text-muted-foreground hover:border-border focus-visible:border-accent-500/60 focus-visible:bg-card/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/25 focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";

export { Input };
