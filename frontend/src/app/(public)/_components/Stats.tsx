import { container } from './container';

const stats = [
  { n: '88%', l: 'Precisión media sobre el conjunto de prueba' },
  { n: '+10.000', l: 'Total de análisis realizados' },
  { n: '8 min', l: 'Duración media de un análisis' },
  { n: '3', l: 'Vías de entrada: texto, enlace y documento' },
];

export default function Stats() {
  return (
    <section aria-label="Resultados" className="bg-surface py-24 max-md:py-18">
      <div className={container}>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map(stat => (
            <div
              key={stat.l}
              className="rounded-[18px] border border-line bg-white px-6.5 py-7.5 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]"
            >
              <b className="block text-[42px] leading-none font-bold tracking-[-0.03em] text-primary">
                {stat.n}
              </b>
              <span className="my-3.5 block h-1 w-8.5 rounded-sm bg-primary" />
              <div className="text-[14.5px] leading-snug font-semibold text-muted">
                {stat.l}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
