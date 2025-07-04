import apiClient from './apiClient.ts';
import { SpeechRequest, SpeechResponse } from '../models/speech.ts';

export const generateSpeech = async (
  request: SpeechRequest
): Promise<SpeechResponse> => {
  try {
    const response = await apiClient.post<SpeechResponse>('/speech', request);
    return response.data;
  } catch (error: any) {
    console.error('Error generating speech:', error);
    throw new Error(error.response?.data?.detail || error.message || 'Failed to generate speech.');
  }
}; 