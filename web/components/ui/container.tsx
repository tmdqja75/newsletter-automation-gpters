import * as React from 'react';
import { cn } from '@/lib/utils';

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}

const Container = React.forwardRef<HTMLDivElement, ContainerProps>(
  ({ className, maxWidth = 'lg', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'mx-auto px-6 sm:px-16',
          {
            'max-w-2xl': maxWidth === 'sm',
            'max-w-3xl': maxWidth === 'md',
            'max-w-4xl': maxWidth === 'lg',
            'max-w-5xl': maxWidth === 'xl',
            'max-w-6xl': maxWidth === '2xl',
          },
          className
        )}
        {...props}
      />
    );
  }
);
Container.displayName = 'Container';

export { Container };
