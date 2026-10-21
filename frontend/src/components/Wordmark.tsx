// translate-y-px recentra el logotipo: Instrument Serif reserva un descendente que «VeriTrust» no usa
export default function Wordmark({ className }: { className: string }) {
  return (
    <span
      className={`translate-y-px font-display leading-none font-normal text-ink italic ${className}`}
    >
      VeriTrust
    </span>
  );
}
