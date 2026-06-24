import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

interface Step {
  label: string;
}

interface StepFormProps {
  steps: Step[];
  currentStep: number;
}

export function StepForm({ steps, currentStep }: StepFormProps) {
  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-center">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium border-2 transition-colors",
                index < currentStep && "bg-primary border-primary text-primary-foreground",
                index === currentStep && "border-primary text-primary",
                index > currentStep && "border-muted-foreground/30 text-muted-foreground"
              )}
            >
              {index < currentStep ? <Check className="h-4 w-4" /> : index + 1}
            </div>
            <span
              className={cn(
                "text-sm whitespace-nowrap",
                index <= currentStep
                  ? "text-foreground font-medium"
                  : "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>
          {index < steps.length - 1 && (
            <div
              className={cn(
                "mx-2 h-0.5 w-8",
                index < currentStep ? "bg-primary" : "bg-muted-foreground/30"
              )}
            />
          )}
        </div>
      ))}
    </div>
  );
}
