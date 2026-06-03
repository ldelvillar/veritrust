import { container } from './container';

const stats = [
  { n: '88%', l: 'de precisión sobre más de 10.000 análisis verificados' },
  { n: '3', l: 'agentes de IA especializados trabajando en cadena' },
  { n: '~2 min', l: 'por análisis medio, de la entrada al informe' },
  { n: '3', l: 'vías de entrada: texto, enlace y documento' },
];

export default function Stats() {
  return (
    <section
      aria-label="Resultados"
      className="bg-[#eeedf8] py-24 max-md:py-18"
    >
      <div className={container}>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map(stat => (
            <div
              key={stat.l}
              className="rounded-[18px] border border-[#e8e6f4] bg-white px-6.5 py-7.5 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]"
            >
              <b className="block text-[42px] leading-none font-bold tracking-[-0.03em] text-primary">
                {stat.n}
              </b>
              <div className="mt-2.5 text-[14.5px] leading-snug font-semibold text-[#6f7090]">
                {stat.l}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
