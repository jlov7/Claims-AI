export interface Precedent {
  claim_id: string; // Align with backend model (snake_case)
  summary: string;
  outcome: string;
  keywords?: string | string[];
  distance?: number; // Raw similarity distance from backend (0–1 scale)
  similarity_score?: number; // Alias for distance (0–1 scale)
}

export interface PrecedentSearchRequest {
  claim_summary: string;
  // query_embedding?: number[]; // Keeping it simple for now, summary is easier for UI
}

export interface PrecedentsApiResponse {
  precedents: Precedent[];
}
