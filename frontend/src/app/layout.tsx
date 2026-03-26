import type { Metadata } from 'next';
import { Onest } from 'next/font/google';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import '@/styles/globals.css';

const onest = Onest({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
});

export const metadata: Metadata = {
  title: 'Detector de Desinformación con IA | VeriTrust',
  description:
    'Detecta afirmaciones médicas falsas con nuestro sistema impulsado por IA. Veritrust proporciona una evaluación de su veracidad, ayudando a identificar información confiable y combatir la desinformación en línea.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${onest.className} relative flex min-h-screen flex-col bg-gray-50 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(217,216,255,0.5),rgba(255,255,255,0.9))] antialiased`}
      >
        <Header />
        <main className="flex flex-1 flex-col">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
