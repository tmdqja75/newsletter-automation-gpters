# UI Components Usage Guide

This directory contains reusable UI components following a consistent design system with zinc color palette and dark mode support.

## Components

### Card

A flexible card container with optional header, content, and footer sections.

```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui';

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description text</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Main content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>;
```

**Props:**

- All standard HTML div attributes
- `className` for custom styling

### Container

Max-width wrapper with responsive padding for consistent page layouts.

```tsx
import { Container } from '@/components/ui';

<Container maxWidth="lg">
  <h1>Page content</h1>
</Container>;
```

**Props:**

- `maxWidth`: 'sm' | 'md' | 'lg' | 'xl' | '2xl' (default: 'lg')
  - sm: max-w-2xl
  - md: max-w-3xl
  - lg: max-w-4xl (default)
  - xl: max-w-5xl
  - 2xl: max-w-6xl
- `className` for additional styling

### Progress

Accessible progress bar with optional label and percentage display.

```tsx
import { Progress } from '@/components/ui';

<Progress value={60} label="Loading" showPercentage />;
```

**Props:**

- `value`: number (0-100, required)
- `label`: string (optional)
- `showPercentage`: boolean (default: false)
- `className` for custom styling

### Badge

Status badges with semantic color variants.

```tsx
import { Badge } from '@/components/ui';

<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info">Info</Badge>
<Badge variant="default">Default</Badge>
```

**Props:**

- `variant`: 'default' | 'success' | 'warning' | 'error' | 'info' (default: 'default')
- `className` for additional styling

### Textarea

Multi-line text input with consistent styling.

```tsx
import { Textarea } from '@/components/ui';

<Textarea placeholder="Enter your message" rows={4} />;
```

**Props:**

- All standard textarea HTML attributes
- `className` for custom styling
- `rows`: number (optional)

## Design Tokens

### Colors

All components use the zinc color palette for consistency:

- **Borders:** `border-zinc-200 dark:border-zinc-800`
- **Backgrounds:** `bg-white dark:bg-black` or `bg-zinc-50 dark:bg-zinc-950`
- **Text:** `text-zinc-700 dark:text-zinc-300` (primary), `text-zinc-600 dark:text-zinc-400` (secondary)
- **Interactive:** `bg-zinc-950 dark:bg-zinc-50` (progress fill)

### Spacing

- Default padding: `p-6`
- Container padding: `px-6 sm:px-16`
- Badge padding: `px-3 py-1`

### Border Radius

- Default: `rounded-lg`
- Badge: `rounded-full`
- Inputs: `rounded-md`

## Dark Mode

All components support dark mode automatically using Tailwind's `dark:` prefix. Ensure your layout has the appropriate dark mode class applied.

## Accessibility

- Progress bars include proper ARIA attributes (`role`, `aria-valuenow`, etc.)
- All components use semantic HTML elements
- ForwardRef pattern allows ref access for focus management

## Importing

You can import components individually or use the barrel export:

```tsx
// Individual imports
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// Barrel import (recommended)
import { Card, Badge, Progress } from '@/components/ui';
```
