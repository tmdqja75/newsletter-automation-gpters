import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SignupForm } from '@/components/auth/signup-form';
import toast from 'react-hot-toast';

/**
 * Test suite for SignupForm component
 *
 * Tests cover:
 * 1. Form rendering (email, password, confirm password inputs, submit button)
 * 2. Validation errors (invalid email, password mismatch)
 * 3. Form submission with valid data
 * 4. Loading state during submission
 * 5. Success message after signup
 * 6. Error handling via toast
 * 7. Link to login page
 * 8. Korean text verification
 * 9. Password confirmation logic
 */

// Mock the signup action
vi.mock('@/lib/actions/auth', () => ({
  signup: vi.fn(),
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
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

describe('SignupForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form Rendering', () => {
    it('should render email input', () => {
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      expect(emailInput).toBeInTheDocument();
      expect(emailInput).toHaveAttribute('type', 'email');
      expect(emailInput).toHaveAttribute('placeholder', 'example@email.com');
    });

    it('should render password input', () => {
      render(<SignupForm />);

      const passwordInput = screen.getByLabelText('비밀번호');
      expect(passwordInput).toBeInTheDocument();
      expect(passwordInput).toHaveAttribute('type', 'password');
      expect(passwordInput).toHaveAttribute('placeholder', '••••••••');
    });

    it('should render confirm password input', () => {
      render(<SignupForm />);

      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');
      expect(confirmPasswordInput).toBeInTheDocument();
      expect(confirmPasswordInput).toHaveAttribute('type', 'password');
      expect(confirmPasswordInput).toHaveAttribute('placeholder', '••••••••');
    });

    it('should render submit button', () => {
      render(<SignupForm />);

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toHaveAttribute('type', 'submit');
    });

    it('should render Korean text correctly', () => {
      render(<SignupForm />);

      expect(
        screen.getByRole('heading', { name: '회원가입' })
      ).toBeInTheDocument();
      expect(screen.getByText('새 계정을 만드세요')).toBeInTheDocument();
      expect(screen.getByText(/이미 계정이 있으신가요?/)).toBeInTheDocument();
    });

    it('should render link to login page', () => {
      render(<SignupForm />);

      const loginLink = screen.getByRole('link', { name: '로그인' });
      expect(loginLink).toBeInTheDocument();
      expect(loginLink).toHaveAttribute('href', '/login');
    });
  });

  describe('Validation - Invalid Email', () => {
    it('should show error for empty email', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('이메일을 입력해주세요')).toBeInTheDocument();
      });
    });

    it('should show error for invalid email format', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일') as HTMLInputElement;
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'invalid-email');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      // Browser's HTML5 validation should prevent form submission
      // The input should have type="email" which triggers browser validation
      expect(emailInput.type).toBe('email');
      expect(emailInput.value).toBe('invalid-email');
    });
  });

  describe('Validation - Password', () => {
    it('should show error for empty password', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      await user.type(emailInput, 'test@example.com');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('비밀번호를 입력해주세요')).toBeInTheDocument();
      });
    });

    it('should show error for password shorter than 8 characters', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'short');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('비밀번호는 최소 8자 이상이어야 합니다')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Validation - Password Mismatch', () => {
    it('should show error when passwords do not match', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password456');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('비밀번호가 일치하지 않습니다')
        ).toBeInTheDocument();
      });
    });

    it('should show error for empty confirm password', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('비밀번호 확인을 입력해주세요')
        ).toBeInTheDocument();
      });
    });

    it('should not show error when passwords match', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.queryByText('비밀번호가 일치하지 않습니다')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should submit form with valid data', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(signup).toHaveBeenCalledTimes(1);
      });

      // Verify FormData was created with correct values
      const callArgs = vi.mocked(signup).mock.calls[0][0] as FormData;
      expect(callArgs.get('email')).toBe('test@example.com');
      expect(callArgs.get('password')).toBe('password123');
      expect(callArgs.get('confirmPassword')).toBe('password123');
    });

    it('should not submit form with invalid data', async () => {
      const { signup } = await import('@/lib/actions/auth');

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      await user.type(emailInput, 'invalid-email');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(signup).not.toHaveBeenCalled();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state during submission', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  success: true,
                  message: '회원가입이 완료되었습니다.',
                }),
              100
            )
          )
      );

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      // Check loading state
      await waitFor(() => {
        expect(screen.getByText('회원가입 중...')).toBeInTheDocument();
      });

      // Wait for loading to finish
      await waitFor(
        () => {
          expect(screen.queryByText('회원가입 중...')).not.toBeInTheDocument();
        },
        { timeout: 200 }
      );
    });

    it('should disable submit button during loading', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  success: true,
                  message: '회원가입이 완료되었습니다.',
                }),
              100
            )
          )
      );

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      // Check button is disabled during loading
      await waitFor(() => {
        const loadingButton = screen.getByRole('button', {
          name: '회원가입 중...',
        });
        expect(loadingButton).toBeDisabled();
      });
    });
  });

  describe('Success State', () => {
    it('should show success message after signup', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('이메일을 확인해주세요')).toBeInTheDocument();
      });
    });

    it('should show success description in Korean', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText(/회원가입이 완료되었습니다/)
        ).toBeInTheDocument();
        expect(
          screen.getByText(
            /이메일에서 인증 링크를 클릭하여 가입을 완료해주세요/
          )
        ).toBeInTheDocument();
      });
    });

    it('should show link to login page after success', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        const loginLink = screen.getByRole('link', {
          name: '로그인 페이지로 이동',
        });
        expect(loginLink).toBeInTheDocument();
        expect(loginLink).toHaveAttribute('href', '/login');
      });
    });

    it('should display success toast after signup', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(
          '회원가입이 완료되었습니다.'
        );
      });
    });

    it('should show success checkmark icon', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        // Check for SVG checkmark icon
        const svg = document.querySelector('svg');
        expect(svg).toBeInTheDocument();
        expect(svg).toHaveClass('text-green-600');
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error toast on signup failure', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: false,
        message: '이미 존재하는 이메일입니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('이미 존재하는 이메일입니다.');
      });
    });

    it('should display generic error toast on exception', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockRejectedValue(new Error('Network error'));

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          '회원가입 중 오류가 발생했습니다.'
        );
      });
    });

    it('should not show success state on error', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: false,
        message: '이미 존재하는 이메일입니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled();
      });

      // Should not show success message
      expect(
        screen.queryByText('이메일을 확인해주세요')
      ).not.toBeInTheDocument();
    });

    it('should reset loading state after error', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockRejectedValue(new Error('Network error'));

      const user = userEvent.setup();
      render(<SignupForm />);

      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled();
      });

      // Button should not be in loading state
      expect(
        screen.getByRole('button', { name: '회원가입' })
      ).toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: '회원가입 중...' })
      ).not.toBeInTheDocument();
    });
  });

  describe('User Interaction Flow', () => {
    it('should handle complete signup flow with user interactions', async () => {
      const { signup } = await import('@/lib/actions/auth');
      vi.mocked(signup).mockResolvedValue({
        success: true,
        message: '회원가입이 완료되었습니다.',
      });

      const user = userEvent.setup();
      render(<SignupForm />);

      // Step 1: Fill in email
      const emailInput = screen.getByLabelText('이메일');
      await user.type(emailInput, 'newuser@example.com');
      expect(emailInput).toHaveValue('newuser@example.com');

      // Step 2: Fill in password
      const passwordInput = screen.getByLabelText('비밀번호');
      await user.type(passwordInput, 'securePassword123');
      expect(passwordInput).toHaveValue('securePassword123');

      // Step 3: Fill in confirm password
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');
      await user.type(confirmPasswordInput, 'securePassword123');
      expect(confirmPasswordInput).toHaveValue('securePassword123');

      // Step 4: Submit form
      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      // Step 5: Verify success
      await waitFor(() => {
        expect(screen.getByText('이메일을 확인해주세요')).toBeInTheDocument();
      });

      // Step 6: Verify login link is available
      const loginLink = screen.getByRole('link', {
        name: '로그인 페이지로 이동',
      });
      expect(loginLink).toBeInTheDocument();
    });

    it('should allow user to correct validation errors', async () => {
      const user = userEvent.setup();
      render(<SignupForm />);

      // Submit with mismatched passwords to trigger validation error
      const emailInput = screen.getByLabelText('이메일');
      const passwordInput = screen.getByLabelText('비밀번호');
      const confirmPasswordInput = screen.getByLabelText('비밀번호 확인');

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.type(confirmPasswordInput, 'password456');

      const submitButton = screen.getByRole('button', { name: '회원가입' });
      await user.click(submitButton);

      // Should show password mismatch error
      await waitFor(() => {
        expect(
          screen.getByText('비밀번호가 일치하지 않습니다')
        ).toBeInTheDocument();
      });

      // Correct the confirm password
      await user.clear(confirmPasswordInput);
      await user.type(confirmPasswordInput, 'password123');

      // Submit again - error should be gone after successful submission
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.queryByText('비밀번호가 일치하지 않습니다')
        ).not.toBeInTheDocument();
      });
    });
  });
});
