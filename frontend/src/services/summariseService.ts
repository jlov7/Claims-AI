import apiClient from './apiClient.ts';

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
    console.log('Summarise API call with request:', request);
    const response = await apiClient.post<SummariseResponse>('/summarise', request);
    console.log('Summarise API response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error fetching summary:', error);
    
    // Extract the most useful error information
    let errorMessage = 'Failed to get summary from server.';
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.data && error.response.data.detail) {
        // Use the detailed error message if available
        errorMessage = error.response.data.detail;
        // Shorten extremely long error messages for UI display
        if (errorMessage.length > 150) {
          errorMessage = errorMessage.substring(0, 147) + '...';
        }
      } else if (error.response.status === 404) {
        errorMessage = 'The summarise endpoint was not found. Please check server configuration.';
      } else if (error.response.status === 500) {
        errorMessage = 'Server error processing this document. Please try again or use a different document.';
      }
    } else if (error.request) {
      // The request was made but no response was received
      errorMessage = 'No response received from the server. Please check your connection.';
    }
    
    throw new Error(errorMessage);
  }
}; 