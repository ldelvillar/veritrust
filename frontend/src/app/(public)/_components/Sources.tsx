import Image, { type StaticImageData } from 'next/image';
import { container } from './container';
import aempsLogo from '@/assets/images/aemps.webp';
import cochraneLogo from '@/assets/images/cochrane.webp';
import fdaLogo from '@/assets/images/fda.webp';
import ministerioLogo from '@/assets/images/ministerio.webp';
import nihLogo from '@/assets/images/nih.png';
import pubmedLogo from '@/assets/images/pubmed.webp';
import whoLogo from '@/assets/images/who.webp';

const logos: { src: StaticImageData; alt: string; height: number }[] = [
  { src: whoLogo, alt: 'OMS', height: 34 },
  { src: cochraneLogo, alt: 'Cochrane', height: 26 },
  { src: nihLogo, alt: 'NIH', height: 46 },
  { src: pubmedLogo, alt: 'PubMed', height: 38 },
  { src: aempsLogo, alt: 'AEMPS', height: 30 },
  { src: fdaLogo, alt: 'FDA', height: 26 },
  { src: ministerioLogo, alt: 'Ministerio de Sanidad', height: 40 },
];

function LogoTrack({ decorative }: { decorative?: boolean }) {
  return (
    <div
      className="logo-track flex shrink-0 items-center gap-18 pr-18"
      aria-hidden={decorative}
    >
      {logos.map(({ src, alt, height }) => (
        <span
          key={alt}
          className="logo-item flex shrink-0 items-center justify-center"
        >
          <Image
            src={src}
            alt={decorative ? '' : alt}
            height={height}
            style={{ height, width: 'auto' }}
          />
        </span>
      ))}
    </div>
  );
}

export default function Sources() {
  return (
    <section
      aria-label="Fuentes médicas"
      className="border-b border-line bg-white py-9.5"
    >
      <div className={container}>
        <p className="mb-6 text-center text-[13px] font-bold tracking-[0.08em] text-faint uppercase">
          Contrastado con fuentes médicas de referencia
        </p>
        <div className="logo-marquee flex w-full overflow-hidden">
          <LogoTrack />
          <LogoTrack decorative />
        </div>
      </div>
    </section>
  );
}
