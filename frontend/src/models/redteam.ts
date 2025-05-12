import { SourceDocument } from './chat.ts'; // Assuming SourceDocument might be reused

// ---------------------------------------------------------------------------
//  Types shared by Red‑Team UI and service calls
// ---------------------------------------------------------------------------

export interface RedTeamPrompt {
  id: string;
  category: string;
  text: string;
  expected_behavior?: string;
}

export interface RedTeamAttempt {
  prompt_id: string;
  prompt_text: string;
  category?: string;
  response_text: string;
  evaluation_notes?: string;
}

export interface SummaryStats {
  total_prompts: number;
  successful_executions: number;
  failed_executions: number;
  overall_score?: number;
}

/**
 * The backend used to return `attempts`, now it might return `results`.
 * Make both optional and we'll pick whichever is present.
 */
export interface RedTeamRunResult {
  attempts: RedTeamAttempt[];
  summary_stats: SummaryStats;
} 