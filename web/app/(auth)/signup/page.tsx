import { SignupForm } from '@/components/auth/signup-form';
import { Container } from '@/components/ui/container';

export default function SignupPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white dark:bg-black">
      <Container maxWidth="md">
        <SignupForm />
      </Container>
    </div>
  );
}
