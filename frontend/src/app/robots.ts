import type { MetadataRoute } from 'next';
import { SITE_CONFIG } from '@/config/site';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: '/app/',
    },
    sitemap: `${SITE_CONFIG.domain}/sitemap.xml`,
  };
}
