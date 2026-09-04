'use client';

import Arrow from '@/assets/Arrow';
import PublicButton from '@/components/PublicButton';

export default function BackButton() {
  return (
    <PublicButton
      variant="outline"
      size="lg"
      onClick={() => window.history.back()}
    >
      <Arrow className="rotate-90" /> Volver atrás
    </PublicButton>
  );
}
