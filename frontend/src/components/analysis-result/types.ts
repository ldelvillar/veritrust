import type { paths } from '@/types/api';

export type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
export type ClaimType = NonNullable<ResultType['claims']>[number];
export type SourceType = NonNullable<ResultType['sources']>[number];
export type Verdict = ResultType['verdict'];

// Vista común al informe propio (autenticado) y al público compartido: este
// último no trae datos de identidad, así que analysis_id es opcional.
export type ReportView = Omit<ResultType, 'user_id' | 'analysis_id'> & {
  analysis_id?: string;
};
