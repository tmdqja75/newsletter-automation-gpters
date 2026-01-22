import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '@/components/auth/login-form';
import * as authActions from '@/lib/actions/auth';
import toast from 'react-hot-toast';

/**
 * Test suite for LoginForm component
 *
 * These tests verify that the login form:
 * - Renders all required form elements correctly
 * - Validates user input according to schema rules
 * - Handles form submission with valid data
 * - Displays appropriate error messages
 * - Shows loading states during submission
 * - Handles server errors gracefully
 * - Provides navigation to signup page
 *
 * Coverage target: >80%
 */

// Mock the auth actions module
vi.mock('@/lib/actions/auth', () => ({
  login: vi.fn(),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// Mock Next.js Link component
vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render email input field', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      expect(emailInput).toBeInTheDocument();
      expect(emailInput).toHaveAttribute('type', 'email');
      expect(emailInput).toHaveAttribute('placeholder', 'example@email.com');
    });

    it('should render password input field', () => {
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText('비밀번호');
      expect(passwordInput).toBeInTheDocument();
      expect(passwordInput).toHaveAttribute('type', 'password');
      expect(passwordInput).toHaveAttribute('placeholder', '••••••••');
    });

    it('should render submit button', () => {
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: '로그인' });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toHaveAttribute('type', 'submit');
      expect(submitButton).not.toBeDisabled();
    });

    it('should render heading and description', () => {
      render(<LoginForm />);

      expect(
        screen.getByRole('heading', { name: '로그인' })
      ).toBeInTheDocument();
      expect(screen.getByText('계정에 로그인하세요')).toBeInTheDocument();
    });

    it('should render signup link', () => {
      render(<LoginForm />);

      const signupLink = screen.getByRole('link', { name: '회원가입' });
      expect(signupLink).toBeInTheDocument();
      expect(signupLink).toHaveAttribute('href', '/signup');
      expect(screen.getByText('계정이 없으신가요?')).toBeInTheDocument();
    });

    it('should have proper form structure', () => {
      const { container } = render(<LoginForm />);

      const form = container.querySelector('form');
      expect(form).toBeInTheDocument();
    });
  });

  describe('Email Validation', () => {
    it('should show error for empty email', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Focus and blur email input without entering value
      await user.click(emailInput);
      await user.tab();

      // Try to submit
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('이메일을 입력해주세요')).toBeInTheDocument();
      });
    });

    it('should have email input with type email for browser validation', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');

      // HTML5 type="email" provides browser-level validation
      expect(emailInput).toHaveAttribute('type', 'email');
    });

    it('should accept valid email format', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');

      await user.type(emailInput, 'test@example.com');

      // Should not show email validation error
      expect(
        screen.queryByText('올바른 이메일 형식이 아닙니다')
      ).not.toBeInTheDocument();
    });

    it('should have proper email placeholder', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');

      // Check that email input has helpful placeholder
      expect(emailInput).toHaveAttribute('placeholder', 'example@email.com');
    });
  });

  describe('Password Validation', () => {
    it('should show error for empty password', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Focus and blur password input without entering value
      await user.click(passwordInput);
      await user.tab();

      // Try to submit
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('비밀번호를 입력해주세요')).toBeInTheDocument();
      });
    });

    it('should show error for password shorter than 8 characters', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Enter short password (7 characters)
      await user.type(passwordInput, 'pass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('비밀번호는 최소 8자 이상이어야 합니다')
        ).toBeInTheDocument();
      });
    });

    it('should accept password with exactly 8 characters', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText('비밀번호');

      await user.type(passwordInput, 'pass1234');

      // Should not show password length error
      expect(
        screen.queryByText('비밀번호는 최소 8자 이상이어야 합니다')
      ).not.toBeInTheDocument();
    });

    it('should accept password longer than 8 characters', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText('비밀번호');

      await user.type(passwordInput, 'longpassword123');

      // Should not show password length error
      expect(
        screen.queryByText('비밀번호는 최소 8자 이상이어야 합니다')
      ).not.toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('should submit form with valid data', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);
      mockLogin.mockResolvedValueOnce({
        success: true,
        message: '로그인 성공',
      });

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Fill in valid data
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      // Submit form
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledTimes(1);
      });

      // Verify FormData contains correct values
      const formData = mockLogin.mock.calls[0][0] as FormData;
      expect(formData.get('email')).toBe('test@example.com');
      expect(formData.get('password')).toBe('password123');
    });

    it('should not submit form with invalid email', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Fill in invalid email
      await user.type(emailInput, 'invalid-email');
      await user.type(passwordInput, 'password123');

      // Submit form
      await user.click(submitButton);

      // Should not call login action
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should not submit form with short password', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Fill in short password
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'pass');

      // Submit form
      await user.click(submitButton);

      // Should not call login action
      expect(mockLogin).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('should show loading state during submission', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      // Create a promise that we can control
      let resolveLogin: (value: { success: boolean; message: string }) => void;
      const loginPromise = new Promise<{ success: boolean; message: string }>(
        (resolve) => {
          resolveLogin = resolve;
        }
      );
      mockLogin.mockReturnValueOnce(loginPromise);

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Fill in valid data
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      // Submit form
      await user.click(submitButton);

      // Check loading state
      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: '로그인 중...' })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('button', { name: '로그인 중...' })
        ).toBeDisabled();
      });

      // Resolve the promise
      resolveLogin!({ success: true, message: '로그인 성공' });

      // Loading should be gone
      await waitFor(() => {
        expect(
          screen.queryByRole('button', { name: '로그인 중...' })
        ).not.toBeInTheDocument();
        expect(
          screen.getByRole('button', { name: '로그인' })
        ).not.toBeDisabled();
      });
    });

    it('should disable submit button during loading', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      let resolveLogin: (value: { success: boolean; message: string }) => void;
      const loginPromise = new Promise<{ success: boolean; message: string }>(
        (resolve) => {
          resolveLogin = resolve;
        }
      );
      mockLogin.mockReturnValueOnce(loginPromise);

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      // Button should be disabled during loading
      await waitFor(() => {
        const loadingButton = screen.getByRole('button', {
          name: '로그인 중...',
        });
        expect(loadingButton).toBeDisabled();
      });

      // Resolve
      resolveLogin!({ success: true, message: '로그인 성공' });

      // Button should be enabled after loading
      await waitFor(() => {
        const button = screen.getByRole('button', { name: '로그인' });
        expect(button).not.toBeDisabled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display server error via toast when login fails', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);
      const mockToastError = vi.mocked(toast.error);

      mockLogin.mockResolvedValueOnce({
        success: false,
        message: '이메일 또는 비밀번호가 올바르지 않습니다',
      });

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          '이메일 또는 비밀번호가 올바르지 않습니다'
        );
      });
    });

    it('should display generic error message on exception', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);
      const mockToastError = vi.mocked(toast.error);

      // Simulate network error or unexpected exception
      mockLogin.mockRejectedValueOnce(new Error('Network error'));

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          '로그인 중 오류가 발생했습니다.'
        );
      });
    });

    it('should reset loading state after error', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      mockLogin.mockRejectedValueOnce(new Error('Network error'));

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      // Loading state should be reset after error
      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: '로그인' })
        ).not.toBeDisabled();
      });
    });
  });

  describe('User Interactions', () => {
    it('should allow typing in email field', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일') as HTMLInputElement;

      await user.type(emailInput, 'user@test.com');

      expect(emailInput.value).toBe('user@test.com');
    });

    it('should allow typing in password field', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const passwordInput = screen.getByLabelText(
        '비밀번호'
      ) as HTMLInputElement;

      await user.type(passwordInput, 'mypassword123');

      expect(passwordInput.value).toBe('mypassword123');
    });

    it('should update input values when user types', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일') as HTMLInputElement;
      const passwordInput = screen.getByLabelText(
        '비밀번호'
      ) as HTMLInputElement;

      // Type in email
      await user.type(emailInput, 'user@test.com');
      expect(emailInput.value).toBe('user@test.com');

      // Clear and type again
      await user.clear(emailInput);
      await user.type(emailInput, 'newemail@test.com');
      expect(emailInput.value).toBe('newemail@test.com');

      // Type in password
      await user.type(passwordInput, 'mypassword');
      expect(passwordInput.value).toBe('mypassword');
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');

      // Start at email input
      await user.click(emailInput);
      expect(emailInput).toHaveFocus();

      // Tab to password
      await user.tab();
      expect(passwordInput).toHaveFocus();

      // Tab to submit button
      await user.tab();
      const submitButton = screen.getByRole('button', { name: '로그인' });
      expect(submitButton).toHaveFocus();
    });
  });

  describe('Multiple Validation Errors', () => {
    it('should show both email and password errors when both are invalid', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Submit without filling anything
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('이메일을 입력해주세요')).toBeInTheDocument();
        expect(screen.getByText('비밀번호를 입력해주세요')).toBeInTheDocument();
      });
    });

    it('should show multiple validation errors for multiple invalid fields', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Submit without filling any fields
      await user.click(submitButton);

      // Should show both email and password errors
      await waitFor(() => {
        expect(screen.getByText('이메일을 입력해주세요')).toBeInTheDocument();
        expect(screen.getByText('비밀번호를 입력해주세요')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      render(<LoginForm />);

      const emailLabel = screen.getByText('이메일');
      const passwordLabel = screen.getByText('비밀번호');

      expect(emailLabel).toBeInTheDocument();
      expect(passwordLabel).toBeInTheDocument();
    });

    it('should associate labels with inputs', () => {
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');

      expect(emailInput).toHaveAttribute('id', 'email');
      expect(passwordInput).toHaveAttribute('id', 'password');
    });

    it('should have proper error message accessibility', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const submitButton = screen.getByRole('button', { name: '로그인' });
      await user.click(submitButton);

      await waitFor(() => {
        const emailError = screen.getByText('이메일을 입력해주세요');
        const passwordError = screen.getByText('비밀번호를 입력해주세요');

        expect(emailError).toBeInTheDocument();
        expect(passwordError).toBeInTheDocument();
        expect(emailError.className).toContain('text-red-600');
        expect(passwordError.className).toContain('text-red-600');
      });
    });
  });

  describe('Korean Text Verification', () => {
    it('should display all Korean text correctly', () => {
      render(<LoginForm />);

      // Header text
      expect(
        screen.getByRole('heading', { name: '로그인' })
      ).toBeInTheDocument();
      expect(screen.getByText('계정에 로그인하세요')).toBeInTheDocument();

      // Form labels
      expect(screen.getByText('이메일')).toBeInTheDocument();
      expect(screen.getByText('비밀번호')).toBeInTheDocument();

      // Button text
      expect(
        screen.getByRole('button', { name: '로그인' })
      ).toBeInTheDocument();

      // Signup link text
      expect(screen.getByText('계정이 없으신가요?')).toBeInTheDocument();
      expect(screen.getByText('회원가입')).toBeInTheDocument();
    });

    it('should show Korean validation error messages', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      // Test empty field errors (guaranteed to show)
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('이메일을 입력해주세요')).toBeInTheDocument();
        expect(screen.getByText('비밀번호를 입력해주세요')).toBeInTheDocument();
      });

      // Test password length validation error
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'short');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('비밀번호는 최소 8자 이상이어야 합니다')
        ).toBeInTheDocument();
      });
    });

    it('should show Korean loading text', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);

      let resolveLogin: (value: { success: boolean; message: string }) => void;
      const loginPromise = new Promise<{ success: boolean; message: string }>(
        (resolve) => {
          resolveLogin = resolve;
        }
      );
      mockLogin.mockReturnValueOnce(loginPromise);

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: '로그인 중...' })
        ).toBeInTheDocument();
      });

      resolveLogin!({ success: true, message: '로그인 성공' });
    });

    it('should show Korean error messages via toast', async () => {
      const user = userEvent.setup();
      const mockLogin = vi.mocked(authActions.login);
      const mockToastError = vi.mocked(toast.error);

      mockLogin.mockRejectedValueOnce(new Error('Network error'));

      render(<LoginForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const submitButton = screen.getByRole('button', { name: '로그인' });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          '로그인 중 오류가 발생했습니다.'
        );
      });
    });
  });
});
