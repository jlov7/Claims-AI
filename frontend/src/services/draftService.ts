import apiClient from './apiClient.ts';
import { DraftStrategyNoteRequest } from '../models/draft.ts';

export const draftStrategyNote = async (
  request: DraftStrategyNoteRequest
): Promise<Blob> => {
  try {
    const response = await apiClient.post<Blob>('/draft', request, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    console.error('Error drafting strategy note:', error);
    // Try to parse the error response if it's a blob of JSON (error from backend)
    if (error.response && error.response.data instanceof Blob) {
      const errorText = await error.response.data.text();
      try {
        const errorJson = JSON.parse(errorText);
        throw new Error(errorJson.detail || 'Failed to draft strategy note. Please check inputs.');
      } catch (e) {
        // If it's not JSON, or parsing fails, throw a generic error
        throw new Error('Failed to draft strategy note and could not parse error response.');
      }
    }
    throw new Error(error.response?.data?.detail || error.message || 'Failed to draft strategy note.');
  }
}; 