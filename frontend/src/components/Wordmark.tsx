// translate-y-px recenters the logotype, since Instrument Serif reserves a descender «VeriTrust» does not use.
export default function Wordmark({ className }: { className: string }) {
  return (
    <span
      className={`translate-y-px font-display leading-none font-normal text-ink italic ${className}`}
    >
      VeriTrust
    </span>
  );
}
