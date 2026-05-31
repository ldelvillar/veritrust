import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { Onest } from 'next/font/google';
import { clientEnv } from '@/env/client';
import '@/env/server';
import '@/styles/globals.css';

const onest = Onest({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
});

export const metadata: Metadata = {
  title: 'Detector de Desinformación con IA | VeriTrust',
  description:
    'Detecta afirmaciones médicas falsas con nuestro sistema impulsado por IA. VeriTrust proporciona una evaluación de su veracidad, ayudando a identificar información confiable y combatir la desinformación en línea.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className={`${onest.className} antialiased`}>
        <ClerkProvider publishableKey={clientEnv.clerkPublishableKey}>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}
