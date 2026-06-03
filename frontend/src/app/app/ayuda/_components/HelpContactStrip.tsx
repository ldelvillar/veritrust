import Link from 'next/link';

import BellIcon from '@/assets/Bell';

interface HelpContactStripProps {
  email: string;
}

export default function HelpContactStrip({ email }: HelpContactStripProps) {
  return (
    <div className="relative mt-10 mb-4 overflow-hidden rounded-[22px] bg-[linear-gradient(125deg,#6557e6,#5345d8_60%,#4a3cc9)] px-8 py-8 text-white shadow-[0_16px_40px_rgba(83,69,216,.26)] md:flex md:items-center md:gap-8 md:px-9">
      <div className="pointer-events-none absolute -right-14 -bottom-20 size-56 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,.14),transparent_62%)]" />
      <div className="relative z-10 flex-1">
        <h3 className="text-[20px] font-bold tracking-[-0.02em] text-white">
          ¿No encuentras lo que buscas?
        </h3>
        <p className="mt-1.5 max-w-105 text-[13.5px] leading-relaxed font-medium text-white/85">
          Nuestro equipo te responde en menos de 24&nbsp;h laborables.
          Escríbenos o agenda una sesión.
        </p>
      </div>
      <div className="relative z-10 mt-5 flex flex-wrap gap-3 md:mt-0 md:shrink-0">
        <a
          href={`mailto:${email}`}
          className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-[14px] font-semibold text-[#5446dc] transition hover:-translate-y-px hover:shadow-[0_12px_26px_rgba(0,0,0,.18)]"
        >
          <BellIcon width={16} height={16} />
          Contactar con soporte
        </a>
        <Link
          href="/demo"
          className="inline-flex items-center gap-2 rounded-xl border border-white/22 bg-white/14 px-5 py-3 text-[14px] font-semibold text-white transition hover:bg-white/22"
        >
          Agendar demo
        </Link>
      </div>
    </div>
  );
}
