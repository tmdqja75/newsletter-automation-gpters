import * as React from 'react';
import { cn } from '@/lib/utils';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  label?: string;
  showPercentage?: boolean;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, label, showPercentage = false, ...props }, ref) => {
    const clampedValue = Math.min(100, Math.max(0, value));

    return (
      <div ref={ref} className={cn('w-full', className)} {...props}>
        {(label || showPercentage) && (
          <div className="mb-2 flex items-center justify-between text-sm">
            {label && (
              <span className="font-medium text-zinc-700 dark:text-zinc-300">
                {label}
              </span>
            )}
            {showPercentage && (
              <span className="text-zinc-600 dark:text-zinc-400">
                {Math.round(clampedValue)}%
              </span>
            )}
          </div>
        )}
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
          role="progressbar"
          aria-valuenow={clampedValue}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-zinc-950 transition-all duration-300 ease-in-out dark:bg-zinc-50"
            style={{ width: `${clampedValue}%` }}
          />
        </div>
      </div>
    );
  }
);
Progress.displayName = 'Progress';

export { Progress };
