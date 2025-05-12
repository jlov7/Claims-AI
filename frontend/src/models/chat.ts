export interface SourceDocument {
  page_content?: string;
  metadata?: { [key: string]: any };

  /** Original filename of the document that produced this chunk */
  file_name?: string;

  /** Chunk identifier (string or number, depending on backend) */
  chunk_id?: string | number;
}

export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  sources?: SourceDocument[];
  confidence_score?: number;
  isLoading?: boolean; // To indicate AI is thinking
  error?: boolean;
  audioUrl?: string; // Added for TTS playback
  isHealing?: boolean; // To indicate AI is attempting self-correction
  self_heal_attempts?: number; // Number of self-healing attempts
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