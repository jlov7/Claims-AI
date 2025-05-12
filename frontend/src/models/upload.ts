export interface UploadedFileStatus {
  id: string; // Unique ID for the frontend list item
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number; // 0-100
  message?: string; // e.g., error message or success message from backend
  backendFileId?: string; // ID assigned by the backend after successful upload
}

export interface UploadResponseItem {
  filename: string;
  message: string;
  success: boolean;
  document_id?: string; // ID of the processed document in the system
  error_details?: string;
}

export interface BatchUploadResponse {
  overall_status: string; // e.g., "Completed", "Completed with errors"
  results: UploadResponseItem[];
} 