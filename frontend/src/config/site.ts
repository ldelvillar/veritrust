export const SITE_CONFIG = {
  domain: 'https://veritrust.es',
  name: 'VeriTrust',
  email: 'lucasvillarv@gmail.com',
  phone: '+34 604 11 26 28',

  seo: {
    defaultTitle: 'Detector de Desinformación Médica con IA | VeriTrust',
    defaultDescription:
      'Detector de noticias falsas de salud con IA. VeriTrust verifica afirmaciones médicas una a una y cita fuentes oficiales (OMS, Cochrane, NIH).',
    appDescription:
      'Detector inteligente de bulos y noticias falsas en salud. Utiliza un sistema multiagente de IA para examinar textos, enlaces y documentos médicos, comparando afirmaciones directas con literatura oficial de forma automática y transparente.',
    defaultImage: '/images/logo-1200x654.png',
    defaultImageWidth: 1200,
    defaultImageHeight: 654,
    defaultImageAlt: 'Logo de VeriTrust',
  },
} as const;
