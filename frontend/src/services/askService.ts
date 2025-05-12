import apiClient from './apiClient.ts';
import type { AskRequest, AskResponse } from '../models/chat.ts';

export const askQuestion = async (query: string): Promise<AskResponse> => {
  const requestData: AskRequest = { query };
  try {
    const response = await apiClient.post<AskResponse>('/ask', requestData);
    return response.data;
  } catch (error: any) {
    console.error('Error asking question:', error);
    // Rethrow or handle as appropriate for your UI
    // For now, rethrow a structured error if possible, or a generic one
    if (error.response && error.response.data) {
      throw new Error(error.response.data.detail || 'Failed to get answer from AI.');
    } else {
      throw new Error('Failed to get answer from AI due to a network or unexpected issue.');
    }
  }
}; 