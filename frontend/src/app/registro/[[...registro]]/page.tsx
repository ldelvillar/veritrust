import type { Metadata } from 'next';
import { SignUp } from '@clerk/nextjs';

import AuthShell from '@/app/_components/AuthShell';
import { clerkAppearance } from '@/config/clerk';

export const metadata: Metadata = {
  title: 'Crear cuenta',
  robots: { index: false },
};

export default function SignUpPage() {
  return (
    <AuthShell>
      <SignUp appearance={clerkAppearance} />
    </AuthShell>
  );
}
