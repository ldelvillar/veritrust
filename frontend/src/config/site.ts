export const SITE_CONFIG = {
  domain: 'https://veritrust.es',
  name: 'VeriTrust',
  email: 'lucasvillarv@gmail.com',
  phone: '+34 604 11 26 28',

  // Holder of the service (LSSI art. 10), cited by the legal notice, terms and privacy policy.
  legal: {
    holder: 'Lucas del Villar Vázquez',
    nif: '54714499Y',
    address: 'Avenida Real de Pinto 87, Módulo 2, Nave Ñ, 28021 Madrid',
  },

  seo: {
    defaultTitle: 'Detector de Desinformación Médica con IA | VeriTrust',
    defaultDescription:
      'Detector de noticias falsas de salud con IA. VeriTrust verifica afirmaciones médicas una a una y cita la literatura científica en que se basa (PubMed, Europe PMC).',
    appDescription:
      'Detector inteligente de bulos y noticias falsas en salud. Utiliza un sistema multiagente de IA para examinar textos, enlaces y documentos médicos, comparando afirmaciones directas con literatura científica de forma automática y transparente.',
    defaultImage: '/images/logo-1200x654.png',
    defaultImageWidth: 1200,
    defaultImageHeight: 654,
    defaultImageAlt: 'Logo de VeriTrust',
  },
} as const;
