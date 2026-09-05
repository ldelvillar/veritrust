'use client';

import { useId, useState } from 'react';
import Check from '@/assets/Check';
import Spinner from '@/assets/Spinner';
import ThumbsDownIcon from '@/assets/ThumbsDown';
import ThumbsUpIcon from '@/assets/ThumbsUp';
import Button from '@/components/Button';
import { useAnalysisFeedback } from '@/hooks/useAnalysisFeedback';
import { VERDICT_META } from './format';
import type { ResultType, Verdict } from './types';

type Feedback = NonNullable<ResultType['feedback']>;

const VERDICT_OPTIONS: Verdict[] = ['real', 'fake', 'uncertain'];

interface FeedbackCardProps {
  analysisId: string;
  initialFeedback: Feedback | null;
}

export default function FeedbackCard({
  analysisId,
  initialFeedback,
}: FeedbackCardProps) {
  const radioName = useId();
  const commentId = useId();
  const { submitFeedback, isSubmitting, error, setError } =
    useAnalysisFeedback();
  const [submitted, setSubmitted] = useState(Boolean(initialFeedback));
  const [reporting, setReporting] = useState(false);
  const [suggestedVerdict, setSuggestedVerdict] = useState<Verdict | null>(
    null
  );
  const [comment, setComment] = useState('');

  const handleConfirm = async () => {
    const success = await submitFeedback(analysisId, { is_correct: true });
    if (success) setSubmitted(true);
  };

  const handleReportSubmit = async () => {
    if (!suggestedVerdict) return;
    const success = await submitFeedback(analysisId, {
      is_correct: false,
      suggested_verdict: suggestedVerdict,
      comment: comment.trim() || null,
    });
    if (success) setSubmitted(true);
  };

  const handleReportCancel = () => {
    if (isSubmitting) return;
    setError(null);
    setSuggestedVerdict(null);
    setComment('');
    setReporting(false);
  };

  if (submitted) {
    return (
      <div className="flex gap-3 rounded-xl border border-success/30 bg-success-soft p-4 print:hidden">
        <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-success/30 bg-white text-success-ink">
          <Check className="size-4.5" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-success-ink">
            ¡Gracias por tu valoración!
          </h4>
          <p className="mt-0.5 text-xs leading-relaxed text-success-ink">
            Nos ayuda a mejorar la precisión del sistema de detección.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-line bg-white p-5 shadow-sm print:hidden">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-ink">
            ¿Es correcto este veredicto?
          </h3>
          <p className="mt-0.5 text-xs text-muted">
            Tu valoración nos ayuda a mejorar el sistema de detección.
          </p>
        </div>
        {!reporting && (
          <div className="flex gap-2">
            <Button
              variant="soft"
              onClick={handleConfirm}
              disabled={isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting ? (
                <Spinner className="size-4 animate-spin" />
              ) : (
                <ThumbsUpIcon className="size-4" />
              )}
              Sí
            </Button>
            <Button
              variant="soft"
              onClick={() => {
                setError(null);
                setReporting(true);
              }}
              disabled={isSubmitting}
            >
              <ThumbsDownIcon className="size-4" />
              No
            </Button>
          </div>
        )}
      </div>

      {reporting && (
        <form
          className="mt-4 flex flex-col gap-4 border-t border-line pt-4"
          onSubmit={e => {
            e.preventDefault();
            handleReportSubmit();
          }}
        >
          <fieldset>
            <legend className="text-sm font-semibold text-body">
              ¿Cuál crees que es el veredicto correcto?
            </legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {VERDICT_OPTIONS.map(verdict => (
                <label
                  key={verdict}
                  className={`cursor-pointer rounded-full border px-3.5 py-1.5 text-sm font-bold transition has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary ${
                    suggestedVerdict === verdict
                      ? `border-transparent ${VERDICT_META[verdict].pill}`
                      : 'border-line-strong bg-white text-body hover:border-primary'
                  }`}
                >
                  <input
                    type="radio"
                    name={radioName}
                    value={verdict}
                    checked={suggestedVerdict === verdict}
                    onChange={() => setSuggestedVerdict(verdict)}
                    className="sr-only"
                  />
                  {VERDICT_META[verdict].label}
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor={commentId}
              className="text-sm font-semibold text-body"
            >
              Comentario (opcional)
            </label>
            <textarea
              id={commentId}
              value={comment}
              maxLength={1000}
              disabled={isSubmitting}
              onChange={e => setComment(e.target.value)}
              placeholder="Ej.: la fuente citada desmiente esta afirmación…"
              className="mt-2 min-h-20 w-full resize-y rounded-lg border border-line-strong bg-surface-subtle px-3.5 py-2.5 font-[inherit] text-sm leading-relaxed text-body transition-all placeholder:text-faint focus:border-primary focus:bg-white focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="submit"
              disabled={!suggestedVerdict || isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting && <Spinner className="size-4 animate-spin" />}
              Enviar valoración
            </Button>
            <Button
              variant="soft"
              onClick={handleReportCancel}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
          </div>
        </form>
      )}

      {error && (
        <p role="alert" className="mt-3 text-sm font-semibold text-danger-ink">
          {error}
        </p>
      )}
    </div>
  );
}
