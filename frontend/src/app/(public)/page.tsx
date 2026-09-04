import type { Metadata } from 'next';
import Cta from './_components/Cta';
import Faq, { faqEntries } from './_components/Faq';
import Features from './_components/Features';
import Hero from './_components/Hero';
import HowItWorks from './_components/HowItWorks';
import Pricing from './_components/Pricing';
import SampleReport from './_components/SampleReport';
import Sources from './_components/Sources';
import UseCases from './_components/UseCases';
import { SITE_CONFIG } from '@/config/site';

export const metadata: Metadata = {
  title: 'Detector de Noticias Falsas de Salud Impulsado por IA',
  alternates: { canonical: '/' },
  description:
    'Detector de desinformación en salud con IA. Verifica afirmaciones médicas una a una, con 88% de precisión y fuentes científicas citadas.',
  keywords: [
    'detector de noticias falsas de salud',
    'verificar bulos médicos',
    'fact-checking médico',
    'desinformación sanitaria',
    'IA verificación salud',
    'comprobar noticias médicas',
  ],
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': `${SITE_CONFIG.domain}/#website`,
      url: SITE_CONFIG.domain,
      name: SITE_CONFIG.name,
      description:
        'Detector de noticias falsas de salud impulsado por un sistema multiagente de IA. Verifica textos, enlaces y documentos médicos con precisión.',
      inLanguage: 'es-ES',
      publisher: {
        '@id': `${SITE_CONFIG.domain}/#organization`,
      },
    },
    {
      '@type': 'Organization',
      '@id': `${SITE_CONFIG.domain}/#organization`,
      name: SITE_CONFIG.name,
      url: SITE_CONFIG.domain,
      logo: {
        '@type': 'ImageObject',
        url: `${SITE_CONFIG.domain}${SITE_CONFIG.seo.defaultImage}`,
      },
      image: `${SITE_CONFIG.domain}${SITE_CONFIG.seo.defaultImage}`,
      email: SITE_CONFIG.email,
      telephone: SITE_CONFIG.phone,
    },
    {
      '@type': 'SoftwareApplication',
      '@id': `${SITE_CONFIG.domain}/#software`,
      name: SITE_CONFIG.name,
      applicationCategory: 'HealthApplication',
      operatingSystem: 'Navegador Web (Windows, macOS, iOS, Android)',
      url: SITE_CONFIG.domain,
      description: SITE_CONFIG.seo.appDescription,
      provider: {
        '@id': `${SITE_CONFIG.domain}/#organization`,
      },
      featureList: [
        'Análisis médico afirmación por afirmación',
        'Extracción automática de artículos web y URLs',
        'Búsqueda en literatura científica (PubMed, Europe PMC)',
        'Soporte multi-idioma integrado',
      ],
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'EUR',
        availability: 'https://schema.org/InStock',
      },
    },
    {
      '@type': 'FAQPage',
      '@id': `${SITE_CONFIG.domain}/#faq`,
      mainEntity: faqEntries.map(({ q, plain }) => ({
        '@type': 'Question',
        name: q,
        acceptedAnswer: { '@type': 'Answer', text: plain },
      })),
    },
  ],
};

export default function Home() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Hero />
      <Sources />
      <HowItWorks />
      <Features />
      <SampleReport />
      <UseCases />
      <Pricing />
      <Faq />
      <Cta />
    </>
  );
}
