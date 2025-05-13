import apiClient from './apiClient.ts';
import type { BatchUploadResponse } from '../models/upload.ts';

export const uploadFiles = async (files: File[]): Promise<BatchUploadResponse> => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file, file.name);
  });

  try {
    console.log("Uploading files to backend:", files.map(f => f.name));
    const response = await apiClient.post<BatchUploadResponse>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      // onUploadProgress: (progressEvent) => { // Optional: for progress tracking
      //   if (progressEvent.total) {
      //     const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      //     console.log(`Upload Progress: ${percentCompleted}%`);
      //     // Here you could call a callback to update UI progress
      //   }
      // },
    });
    console.log("Upload response from backend:", response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error uploading files:', error);
    if (error.response && error.response.data) {
      // If backend sends a BatchUploadResponse even for errors, use it
      if (error.response.data.results && error.response.data.overall_status) {
        return error.response.data as BatchUploadResponse;
      }
      // Otherwise, construct a generic error response
      const errorMsg = error.response.data.detail || 'Failed to upload files.';
      return {
        overall_status: "Error",
        results: files.map(f => ({
          filename: f.name,
          success: false,
          message: errorMsg,
        })),
        uploaded: 0,
        ingested: 0,
        errors: [errorMsg]
      };
    }
    return {
      overall_status: "Error",
      results: files.map(f => ({
        filename: f.name,
        success: false,
        message: 'Network error or unexpected issue during upload.',
      })),
      uploaded: 0,
      ingested: 0,
      errors: ['Network error or unexpected issue during upload.']
    };
  }
}; 