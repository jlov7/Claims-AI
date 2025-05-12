export interface SpeechRequest {
  text: string;
  speaker_id?: string; // Optional: backend might have a default
  language_id?: string; // Optional: backend might have a default
}

export interface SpeechResponse {
  audio_url: string;
  message: string; // Confirmation message from backend
  filename: string; // Filename in Minio
} 