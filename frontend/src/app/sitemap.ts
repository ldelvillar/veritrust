import type { MetadataRoute } from 'next';
import { SITE_CONFIG } from '@/config/site';

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  return [
    {
      url: SITE_CONFIG.domain,
      lastModified,
      changeFrequency: 'weekly',
      priority: 1,
    },
    {
      url: `${SITE_CONFIG.domain}/contacto`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${SITE_CONFIG.domain}/demo`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${SITE_CONFIG.domain}/aviso-legal`,
      lastModified,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${SITE_CONFIG.domain}/terminos-y-condiciones`,
      lastModified,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${SITE_CONFIG.domain}/politica-de-privacidad`,
      lastModified,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ];
}
