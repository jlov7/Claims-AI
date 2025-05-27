export interface UploadedFileStatus {
  id: string; // Unique ID for the frontend list item
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress?: number; // 0-100
  message?: string; // e.g., error message or success message from backend
  backendFileId?: string; // ID assigned by the backend after successful upload
  ingested?: boolean; // Whether the document was successfully ingested into the vector store
  document_id?: string; // ID of the processed document in the system
}

export interface UploadResponseItem {
  filename: string;
  message: string;
  success: boolean;
  document_id?: string; // ID of the processed document in the system
  error_details?: string;
  ingested?: boolean; // Whether the document was successfully ingested into the vector store
}

export interface BatchUploadResponse {
  overall_status: string; // e.g., "Completed", "Completed with errors"
  results: UploadResponseItem[];
  uploaded: number; // Total number of files uploaded
  ingested: number; // Total number of files successfully ingested
  errors: string[]; // List of error messages
}
