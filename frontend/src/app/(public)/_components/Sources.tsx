import { container } from './container';

const sources = [
  'OMS',
  'Cochrane',
  'NIH',
  'PubMed',
  'Europe PMC',
  'AEMPS',
  'FDA',
  'Ministerio de Sanidad',
];

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
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-5">
          {sources.map(s => (
            <span
              key={s}
              className="text-[21px] font-bold tracking-tight text-faint grayscale transition hover:text-body hover:grayscale-0"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
