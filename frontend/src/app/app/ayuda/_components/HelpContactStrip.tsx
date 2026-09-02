import BellIcon from '@/assets/Bell';
import Button from '@/components/Button';

interface HelpContactStripProps {
  email: string;
}

export default function HelpContactStrip({ email }: HelpContactStripProps) {
  return (
    <div className="relative mt-10 mb-4 overflow-hidden rounded-[22px] bg-primary px-8 py-8 text-white shadow-[0_16px_40px_rgba(12,79,82,.26)] md:flex md:items-center md:gap-8 md:px-9">
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
        <Button href={`mailto:${email}`} variant="light">
          <BellIcon width={16} height={16} />
          Contactar con soporte
        </Button>
        <Button href="/demo" variant="outline">
          Agendar demo
        </Button>
      </div>
    </div>
  );
}
