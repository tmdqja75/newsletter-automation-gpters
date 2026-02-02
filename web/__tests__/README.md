# Testing Documentation

This directory contains the test suite for the web application, built with Vitest.

## Overview

The test suite provides comprehensive coverage for:

- Environment variable validation
- Supabase client utilities (browser and server)
- Type safety and error handling

## Test Structure

```
__tests__/
├── lib/
│   ├── env.test.ts                  # Environment validation tests
│   └── supabase/
│       ├── client.test.ts           # Browser client tests
│       └── server.test.ts           # Server client tests
└── README.md                        # This file
```

## Running Tests

### Basic Commands

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Advanced Options

```bash
# Run specific test file
npm run test -- __tests__/lib/env.test.ts

# Run tests matching pattern
npm run test -- --grep "Environment Validation"

# Run tests in a specific directory
npm run test -- __tests__/lib/supabase

# Update snapshots (if using)
npm run test -- -u
```

## Test Configuration

### vitest.config.ts

The Vitest configuration includes:

- **Environment**: `happy-dom` for DOM simulation
- **Globals**: Enabled for familiar test syntax
- **Setup Files**: `vitest.setup.ts` for test initialization
- **Path Aliases**: `@/` resolves to project root
- **Coverage**: V8 provider with text, JSON, and HTML reports

### vitest.setup.ts

The setup file:

- Clears all mocks before each test
- Mocks Next.js `next/headers` module
- Sets up default environment variables for testing

## Test Coverage

Current coverage:

- **Overall**: 94.73%
- **lib/env.ts**: 90%
- **lib/supabase/client.ts**: 100%
- **lib/supabase/server.ts**: 100%

## Writing Tests

### Example Test Structure

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('Feature Name', () => {
  beforeEach(() => {
    // Setup before each test
    vi.clearAllMocks();
  });

  describe('Specific Functionality', () => {
    it('should do something specific', () => {
      // Arrange
      const input = 'test';

      // Act
      const result = functionUnderTest(input);

      // Assert
      expect(result).toBe('expected');
    });
  });
});
```

### Mocking

#### Mocking Modules

```typescript
vi.mock('module-name', () => ({
  functionName: vi.fn(() => 'mocked value'),
}));
```

#### Mocking Environment Variables

```typescript
// In test file
const originalEnv = process.env.SOME_VAR;
process.env.SOME_VAR = 'test-value';

// Cleanup
afterEach(() => {
  process.env.SOME_VAR = originalEnv;
});
```

## Test Files

### env.test.ts

Tests for environment variable validation:

- Validates all required environment variables
- Tests validation failures for missing/invalid values
- Verifies type safety
- Tests error messages

**Key test cases:**

- Valid environment configuration
- Missing environment variables
- Invalid URL formats
- Short API keys (minimum length validation)
- Invalid NODE_ENV values

### supabase/client.test.ts

Tests for browser-side Supabase client:

- Creates client with correct credentials
- Verifies client structure
- Tests error handling
- Validates environment variable usage

**Key test cases:**

- Client creation
- Environment variable usage
- Client instance isolation
- Auth/database/storage methods availability

### supabase/server.test.ts

Tests for server-side Supabase clients:

- Regular server client with cookies
- Admin client with service role key
- Cookie management
- Error handling

**Key test cases:**

- Server client creation
- Admin client creation
- Cookie handler configuration
- Cookie error handling
- Service role vs anon key usage

## Best Practices

### 1. Test Organization

- Group related tests using `describe` blocks
- Use clear, descriptive test names
- Follow Arrange-Act-Assert pattern

### 2. Test Isolation

- Each test should be independent
- Clean up after tests (mocks, environment variables)
- Use `beforeEach` and `afterEach` for setup/teardown

### 3. Mocking

- Mock external dependencies
- Don't mock the code you're testing
- Clear mocks between tests

### 4. Assertions

- Test one thing per test
- Use specific matchers (`toBe`, `toEqual`, `toContain`)
- Add meaningful error messages when needed

### 5. Coverage

- Aim for high coverage (>80%)
- Focus on critical paths
- Don't sacrifice test quality for coverage numbers

## Common Issues and Solutions

### Issue: Module not found

**Solution**: Check path aliases in `vitest.config.ts` and `tsconfig.json`

### Issue: Environment variables not set

**Solution**: Verify `vitest.setup.ts` sets all required env vars

### Issue: Tests failing due to module caching

**Solution**: Use `vi.resetModules()` or restructure test imports

### Issue: Async tests timing out

**Solution**: Use `async`/`await` properly and increase timeout if needed

## CI/CD Integration

Tests run automatically in CI/CD pipeline:

- Triggered on push/PR to `main` and `dev` branches
- Must pass before merge
- Coverage reports generated

See `.github/workflows/ci-web.yml` for CI configuration.

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Vitest API Reference](https://vitest.dev/api/)
- [Happy DOM](https://github.com/capricorn86/happy-dom)
