import type { Metadata } from 'next';
import Cta from './_components/Cta';
import Faq, { faqEntries } from './_components/Faq';
import Features from './_components/Features';
import Hero from './_components/Hero';
import HowItWorks from './_components/HowItWorks';
import Pricing from './_components/Pricing';
import SampleReport from './_components/SampleReport';
import Sources from './_components/Sources';
import Stats from './_components/Stats';
import UseCases from './_components/UseCases';

export const metadata: Metadata = {
  title: 'VeriTrust | Detector de Noticias Falsas de Salud Impulsado por IA',
  description:
    'VeriTrust es un detector de noticias falsas de salud impulsado por un sistema multiagente de IA. Verifica textos, enlaces y documentos médicos afirmación por afirmación, con un 88% de precisión y fuentes citadas (OMS, Cochrane, NIH).',
  keywords: [
    'detector de noticias falsas de salud',
    'verificar bulos médicos',
    'fact-checking médico',
    'desinformación sanitaria',
    'IA verificación salud',
    'comprobar noticias médicas',
  ],
  openGraph: {
    type: 'website',
    siteName: 'VeriTrust',
    locale: 'es_ES',
    title: 'Detector de noticias falsas de salud con IA | VeriTrust',
    description:
      'Verifica afirmaciones médicas en segundos. Un sistema multiagente de IA analiza texto, enlaces y documentos y devuelve una puntuación de credibilidad explicada.',
  },
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'SoftwareApplication',
      name: 'VeriTrust',
      applicationCategory: 'HealthApplication',
      operatingSystem: 'Web',
      description:
        'Detector de noticias falsas de salud con un sistema multiagente de IA que verifica textos, enlaces y documentos médicos afirmación por afirmación.',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' },
    },
    {
      '@type': 'FAQPage',
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
      <Stats />
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
