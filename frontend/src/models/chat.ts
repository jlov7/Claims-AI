export interface SourceDocument {
  file_name?: string;
  page_content?: string; // chunk_content alias
  chunk_id?: string | number;
  score?: number;
  metadata?: { [key: string]: any };
}

export interface ChatMessage {
  id: string;
  sender: "user" | "ai";
  text: string;
  sources?: SourceDocument[];
  confidence_score?: number;
  isLoading?: boolean; // To indicate AI is thinking
  error?: boolean;
  audioUrl?: string; // Added for TTS playback
  isHealing?: boolean; // To indicate AI is attempting self-correction
  self_heal_attempts?: number; // Number of self-healing attempts
  isPlaying?: boolean; // UI flag
}

export interface AskRequest {
  query: string;
}

export interface AskResponse {
  answer: string;
  sources: SourceDocument[];
  confidence_score?: number;
  self_heal_attempts?: number;
}
