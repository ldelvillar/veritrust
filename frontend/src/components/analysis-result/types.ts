import type { components, paths } from '@/types/api';

export type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
export type ClaimType = NonNullable<ResultType['claims']>[number];
export type SourceType = NonNullable<ResultType['sources']>[number];
export type Verdict = ResultType['verdict'];
export type ConfidenceLevel = NonNullable<ResultType['confidence_level']>;
export type AnalysisStage = NonNullable<ResultType['stage']>;
export type ErrorCode = components['schemas']['ErrorCode'];

// View shared by the owner's report and the public shared one, which carries no identity data, so analysis_id and origin are optional.
export type ReportView = Omit<
  ResultType,
  'user_id' | 'analysis_id' | 'origin'
> & {
  analysis_id?: string;
  origin?: string;
};
