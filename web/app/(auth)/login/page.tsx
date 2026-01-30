import { LoginForm } from '@/components/auth/login-form';
import { Container } from '@/components/ui/container';

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white dark:bg-black">
      <Container maxWidth="md">
        <LoginForm />
      </Container>
    </div>
  );
}
