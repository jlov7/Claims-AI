export interface Precedent {
  claim_id: string; // Align with backend model (snake_case)
  summary: string;
  outcome: string;
  keywords: string[];
  similarity_score?: number; // Align with backend model (snake_case)
}

export interface PrecedentSearchRequest {
  claim_summary: string;
  // query_embedding?: number[]; // Keeping it simple for now, summary is easier for UI
}

export interface PrecedentsApiResponse {
  precedents: Precedent[];
} 