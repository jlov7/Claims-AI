import apiClient from './apiClient.js';

export interface SummariseRequest {
  document_id?: string;
  content?: string;
}

export interface SummariseResponse {
  summary: string;
  original_document_id?: string;
  original_content_preview?: string;
}

export const summarise = async (
  request: SummariseRequest
): Promise<SummariseResponse> => {
  try {
    const response = await apiClient.post<SummariseResponse>('/summarise', request);
    return response.data;
  } catch (error: any) {
    console.error('Error fetching summary:', error);
    throw new Error(error.response?.data?.detail || 'Failed to get summary from server.');
  }
}; 