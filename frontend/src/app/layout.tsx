import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { Onest } from 'next/font/google';
import { clientEnv } from '@/env/client';
import '@/env/server';
import { SITE_CONFIG } from '@/config/site';
import '@/styles/globals.css';

const onest = Onest({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800', '900'],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_CONFIG.domain),
  title: {
    default: SITE_CONFIG.seo.defaultTitle,
    template: `%s | ${SITE_CONFIG.name}`,
  },
  description: SITE_CONFIG.seo.defaultDescription,
  openGraph: {
    title: SITE_CONFIG.seo.defaultTitle,
    description: SITE_CONFIG.seo.defaultDescription,
    siteName: SITE_CONFIG.name,
    type: 'website',
    url: new URL(SITE_CONFIG.domain),
    locale: 'es_ES',
    images: [
      {
        url: SITE_CONFIG.seo.defaultImage,
        width: SITE_CONFIG.seo.defaultImageWidth,
        height: SITE_CONFIG.seo.defaultImageHeight,
        alt: SITE_CONFIG.seo.defaultImageAlt,
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_CONFIG.seo.defaultTitle,
    description: SITE_CONFIG.seo.defaultDescription,
    images: [
      {
        url: SITE_CONFIG.seo.defaultImage,
        width: SITE_CONFIG.seo.defaultImageWidth,
        height: SITE_CONFIG.seo.defaultImageHeight,
        alt: SITE_CONFIG.seo.defaultImageAlt,
      },
    ],
  },
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
