import QuestionIcon from '@/assets/Question';
import Tooltip from '@/components/Tooltip';

export default function InfoHint({
  label,
  text,
}: {
  label: string;
  text: string;
}) {
  return (
    <Tooltip
      ariaLabel={`Cómo se calcula: ${label}`}
      trigger={<QuestionIcon className="size-4" />}
      buttonClassName="grid size-4 place-items-center rounded-full text-muted transition hover:text-body focus:text-body focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
      panelClassName="absolute top-full right-0 z-10 mt-2 w-56 rounded-lg bg-ink px-3 py-2 text-left text-xs leading-snug font-medium text-white shadow-lg transition-opacity"
    >
      {text}
    </Tooltip>
  );
}
