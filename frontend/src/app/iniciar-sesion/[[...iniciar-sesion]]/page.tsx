import type { Metadata } from 'next';
import { SignIn } from '@clerk/nextjs';

import AuthShell from '@/app/_components/AuthShell';
import { clerkAppearance } from '@/config/clerk';

export const metadata: Metadata = {
  title: 'Iniciar sesión',
  robots: { index: false },
};

export default function SignInPage() {
  return (
    <AuthShell legalNotice>
      <SignIn appearance={clerkAppearance} />
    </AuthShell>
  );
}
