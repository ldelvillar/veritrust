import QuestionIcon from '@/assets/Question';

export default function InfoHint({
  label,
  text,
}: {
  label: string;
  text: string;
}) {
  return (
    <span className="group relative inline-flex shrink-0">
      <button
        type="button"
        aria-label={`Cómo se calcula: ${label}`}
        className="grid size-4 place-items-center rounded-full text-faint transition hover:text-muted focus:text-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        <QuestionIcon className="size-4" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute top-full right-0 z-10 mt-2 w-56 rounded-lg bg-ink px-3 py-2 text-left text-xs leading-snug font-medium text-white opacity-0 shadow-lg transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
