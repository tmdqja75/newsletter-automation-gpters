import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { loginSchema, signupSchema } from '@/lib/validation/auth';
import type { LoginInput, SignupInput } from '@/lib/validation/auth';

/**
 * Test suite for authentication validation schemas
 *
 * These tests verify that the auth validation properly:
 * - Accepts valid login and signup inputs
 * - Rejects invalid email formats
 * - Enforces password minimum length requirements
 * - Validates password confirmation matching
 * - Provides Korean error messages
 */
describe('Authentication Validation', () => {
  describe('loginSchema', () => {
    describe('Valid Inputs', () => {
      it('should accept valid email and password', () => {
        const validInput = {
          email: 'test@example.com',
          password: 'password123',
        };

        const result = loginSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data).toEqual(validInput);
          expect(result.data.email).toBe('test@example.com');
          expect(result.data.password).toBe('password123');
        }
      });

      it('should accept password exactly 8 characters long', () => {
        const validInput = {
          email: 'user@test.com',
          password: '12345678',
        };

        const result = loginSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.password).toBe('12345678');
          expect(result.data.password.length).toBe(8);
        }
      });

      it('should accept various valid email formats', () => {
        const validEmails = [
          'simple@example.com',
          'user.name@example.com',
          'user+tag@example.co.kr',
          'test123@subdomain.example.com',
          'a@b.co',
        ];

        validEmails.forEach((email) => {
          const result = loginSchema.safeParse({
            email,
            password: 'password123',
          });

          expect(result.success).toBe(true);
        });
      });

      it('should accept long passwords', () => {
        const validInput = {
          email: 'test@example.com',
          password: 'very-long-password-with-many-characters-123456789',
        };

        const result = loginSchema.safeParse(validInput);

        expect(result.success).toBe(true);
      });
    });

    describe('Invalid Email Format', () => {
      it('should reject email without @ symbol', () => {
        const invalidInput = {
          email: 'notanemail',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '올바른 이메일 형식이 아닙니다'
          );
        }
      });

      it('should reject email without domain', () => {
        const invalidInput = {
          email: 'user@',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '올바른 이메일 형식이 아닙니다'
          );
        }
      });

      it('should reject email without username', () => {
        const invalidInput = {
          email: '@example.com',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
        }
      });

      it('should reject email with spaces', () => {
        const invalidInput = {
          email: 'user @example.com',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '올바른 이메일 형식이 아닙니다'
          );
        }
      });

      it('should reject empty email with Korean error message', () => {
        const invalidInput = {
          email: '',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '이메일을 입력해주세요'
          );
        }
      });

      it('should reject multiple @ symbols', () => {
        const invalidInput = {
          email: 'user@@example.com',
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
        }
      });
    });

    describe('Invalid Password', () => {
      it('should reject password shorter than 8 characters', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '1234567',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
          expect(result.error.issues[0].message).toBe(
            '비밀번호는 최소 8자 이상이어야 합니다'
          );
        }
      });

      it('should reject empty password with Korean error message', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
          expect(result.error.issues[0].message).toBe(
            '비밀번호를 입력해주세요'
          );
        }
      });

      it('should reject 1 character password', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '1',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
        }
      });
    });

    describe('Missing Fields', () => {
      it('should reject missing email field', () => {
        const invalidInput = {
          password: 'password123',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
        }
      });

      it('should reject missing password field', () => {
        const invalidInput = {
          email: 'test@example.com',
        };

        const result = loginSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
        }
      });

      it('should reject empty object', () => {
        const result = loginSchema.safeParse({});

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues.length).toBeGreaterThanOrEqual(2);
        }
      });
    });

    describe('Type Safety', () => {
      it('should provide typed LoginInput', () => {
        const validInput: LoginInput = {
          email: 'test@example.com',
          password: 'password123',
        };

        const result = loginSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          const typedData: LoginInput = result.data;
          expect(typedData.email).toBeDefined();
          expect(typedData.password).toBeDefined();
        }
      });
    });
  });

  describe('signupSchema', () => {
    describe('Valid Inputs', () => {
      it('should accept valid signup data with matching passwords', () => {
        const validInput = {
          email: 'newuser@example.com',
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data).toEqual(validInput);
          expect(result.data.email).toBe('newuser@example.com');
          expect(result.data.password).toBe('password123');
          expect(result.data.confirmPassword).toBe('password123');
        }
      });

      it('should accept passwords exactly 8 characters long', () => {
        const validInput = {
          email: 'user@test.com',
          password: '12345678',
          confirmPassword: '12345678',
        };

        const result = signupSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.password.length).toBe(8);
          expect(result.data.confirmPassword.length).toBe(8);
        }
      });

      it('should accept various valid email formats', () => {
        const validEmails = [
          'simple@example.com',
          'user.name@example.com',
          'user+tag@example.co.kr',
          'test123@subdomain.example.com',
        ];

        validEmails.forEach((email) => {
          const result = signupSchema.safeParse({
            email,
            password: 'password123',
            confirmPassword: 'password123',
          });

          expect(result.success).toBe(true);
        });
      });

      it('should accept long matching passwords', () => {
        const longPassword = 'very-long-password-with-many-characters-123456789';
        const validInput = {
          email: 'test@example.com',
          password: longPassword,
          confirmPassword: longPassword,
        };

        const result = signupSchema.safeParse(validInput);

        expect(result.success).toBe(true);
      });
    });

    describe('Password Mismatch', () => {
      it('should reject when passwords do not match', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'password123',
          confirmPassword: 'password456',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('confirmPassword');
          expect(result.error.issues[0].message).toBe(
            '비밀번호가 일치하지 않습니다'
          );
        }
      });

      it('should reject when passwords differ by one character', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'password123',
          confirmPassword: 'password124',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('confirmPassword');
          expect(result.error.issues[0].message).toBe(
            '비밀번호가 일치하지 않습니다'
          );
        }
      });

      it('should reject when passwords differ by case', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'Password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('confirmPassword');
          expect(result.error.issues[0].message).toBe(
            '비밀번호가 일치하지 않습니다'
          );
        }
      });

      it('should reject when confirmPassword has trailing space', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'password123',
          confirmPassword: 'password123 ',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('confirmPassword');
        }
      });
    });

    describe('Invalid Email Format', () => {
      it('should reject invalid email with Korean error message', () => {
        const invalidInput = {
          email: 'notanemail',
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '올바른 이메일 형식이 아닙니다'
          );
        }
      });

      it('should reject empty email', () => {
        const invalidInput = {
          email: '',
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
          expect(result.error.issues[0].message).toBe(
            '이메일을 입력해주세요'
          );
        }
      });

      it('should reject email without domain', () => {
        const invalidInput = {
          email: 'user@',
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
        }
      });
    });

    describe('Invalid Password', () => {
      it('should reject password shorter than 8 characters', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '1234567',
          confirmPassword: '1234567',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
          expect(result.error.issues[0].message).toBe(
            '비밀번호는 최소 8자 이상이어야 합니다'
          );
        }
      });

      it('should reject empty password', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '',
          confirmPassword: '',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
          expect(result.error.issues[0].message).toBe(
            '비밀번호를 입력해주세요'
          );
        }
      });

      it('should reject password with only 7 characters', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'pass123',
          confirmPassword: 'pass123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
        }
      });
    });

    describe('Invalid Confirm Password', () => {
      it('should reject empty confirmPassword', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'password123',
          confirmPassword: '',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          const confirmPasswordError = result.error.issues.find((issue) =>
            issue.path.includes('confirmPassword')
          );
          expect(confirmPasswordError).toBeDefined();
          expect(confirmPasswordError?.message).toBe(
            '비밀번호 확인을 입력해주세요'
          );
        }
      });

      it('should reject when confirmPassword is too short even if matching', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: '1234567',
          confirmPassword: '1234567',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          // Should fail on password length before confirm password check
          expect(result.error.issues[0].path).toContain('password');
        }
      });
    });

    describe('Missing Fields', () => {
      it('should reject missing email field', () => {
        const invalidInput = {
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('email');
        }
      });

      it('should reject missing password field', () => {
        const invalidInput = {
          email: 'test@example.com',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('password');
        }
      });

      it('should reject missing confirmPassword field', () => {
        const invalidInput = {
          email: 'test@example.com',
          password: 'password123',
        };

        const result = signupSchema.safeParse(invalidInput);

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues[0].path).toContain('confirmPassword');
        }
      });

      it('should reject empty object', () => {
        const result = signupSchema.safeParse({});

        expect(result.success).toBe(false);
        if (!result.success) {
          expect(result.error.issues.length).toBeGreaterThanOrEqual(3);
        }
      });
    });

    describe('Type Safety', () => {
      it('should provide typed SignupInput', () => {
        const validInput: SignupInput = {
          email: 'test@example.com',
          password: 'password123',
          confirmPassword: 'password123',
        };

        const result = signupSchema.safeParse(validInput);

        expect(result.success).toBe(true);
        if (result.success) {
          const typedData: SignupInput = result.data;
          expect(typedData.email).toBeDefined();
          expect(typedData.password).toBeDefined();
          expect(typedData.confirmPassword).toBeDefined();
        }
      });
    });
  });

  describe('Schema Exports', () => {
    it('should export loginSchema as Zod object', () => {
      expect(loginSchema).toBeDefined();
      expect(loginSchema).toBeInstanceOf(z.ZodObject);
    });

    it('should export signupSchema as Zod schema with refinement', () => {
      expect(signupSchema).toBeDefined();
      // signupSchema is a ZodEffects due to .refine()
      // Check that it has the parse method (all Zod schemas have this)
      expect(typeof signupSchema.parse).toBe('function');
      expect(typeof signupSchema.safeParse).toBe('function');
    });
  });

  describe('Error Messages in Korean', () => {
    it('should provide all Korean error messages for login', () => {
      const testCases = [
        {
          input: { email: '', password: '' },
          expectedMessage: '이메일을 입력해주세요',
        },
        {
          input: { email: 'invalid', password: 'password123' },
          expectedMessage: '올바른 이메일 형식이 아닙니다',
        },
        {
          input: { email: 'test@example.com', password: '' },
          expectedMessage: '비밀번호를 입력해주세요',
        },
        {
          input: { email: 'test@example.com', password: '1234567' },
          expectedMessage: '비밀번호는 최소 8자 이상이어야 합니다',
        },
      ];

      testCases.forEach(({ input, expectedMessage }) => {
        const result = loginSchema.safeParse(input);
        expect(result.success).toBe(false);
        if (!result.success) {
          const hasExpectedMessage = result.error.issues.some(
            (issue) => issue.message === expectedMessage
          );
          expect(hasExpectedMessage).toBe(true);
        }
      });
    });

    it('should provide all Korean error messages for signup', () => {
      const testCases = [
        {
          input: {
            email: '',
            password: 'password123',
            confirmPassword: 'password123',
          },
          expectedMessage: '이메일을 입력해주세요',
        },
        {
          input: {
            email: 'invalid',
            password: 'password123',
            confirmPassword: 'password123',
          },
          expectedMessage: '올바른 이메일 형식이 아닙니다',
        },
        {
          input: {
            email: 'test@example.com',
            password: '',
            confirmPassword: '',
          },
          expectedMessage: '비밀번호를 입력해주세요',
        },
        {
          input: {
            email: 'test@example.com',
            password: '1234567',
            confirmPassword: '1234567',
          },
          expectedMessage: '비밀번호는 최소 8자 이상이어야 합니다',
        },
        {
          input: {
            email: 'test@example.com',
            password: 'password123',
            confirmPassword: '',
          },
          expectedMessage: '비밀번호 확인을 입력해주세요',
        },
        {
          input: {
            email: 'test@example.com',
            password: 'password123',
            confirmPassword: 'password456',
          },
          expectedMessage: '비밀번호가 일치하지 않습니다',
        },
      ];

      testCases.forEach(({ input, expectedMessage }) => {
        const result = signupSchema.safeParse(input);
        expect(result.success).toBe(false);
        if (!result.success) {
          const hasExpectedMessage = result.error.issues.some(
            (issue) => issue.message === expectedMessage
          );
          expect(hasExpectedMessage).toBe(true);
        }
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle Unicode characters in email', () => {
      const invalidInput = {
        email: 'test@한글도메인.com',
        password: 'password123',
      };

      const result = loginSchema.safeParse(invalidInput);

      // Most validators reject Unicode domains, but behavior may vary
      expect(result.success).toBe(false);
    });

    it('should handle whitespace-only password', () => {
      const invalidInput = {
        email: 'test@example.com',
        password: '        ',
        confirmPassword: '        ',
      };

      const result = signupSchema.safeParse(invalidInput);

      // 8 spaces should technically pass length check but be invalid for security
      // This tests current behavior - may want to add .trim() in future
      expect(result.success).toBe(true);
    });

    it('should handle special characters in password', () => {
      const validInput = {
        email: 'test@example.com',
        password: '!@#$%^&*()',
        confirmPassword: '!@#$%^&*()',
      };

      const result = signupSchema.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should handle very long email addresses', () => {
      const longEmail =
        'verylongemailaddresswithnumerouscharacters1234567890@subdomain.example.com';
      const validInput = {
        email: longEmail,
        password: 'password123',
        confirmPassword: 'password123',
      };

      const result = signupSchema.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should handle null values', () => {
      const invalidInput = {
        email: null,
        password: null,
      };

      const result = loginSchema.safeParse(invalidInput);

      expect(result.success).toBe(false);
    });

    it('should handle undefined values', () => {
      const invalidInput = {
        email: undefined,
        password: undefined,
      };

      const result = loginSchema.safeParse(invalidInput);

      expect(result.success).toBe(false);
    });
  });
});
