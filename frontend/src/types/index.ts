export type SourceType = 'url' | 'file' | 'text';

export interface AnalysisDetail {
  id: string;
  label: string;
  confidence: number | string;
  explanation: string;
}
