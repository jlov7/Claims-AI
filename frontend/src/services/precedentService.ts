import apiClient from './apiClient.js';
import { PrecedentSearchRequest, PrecedentsApiResponse } from '../models/precedent.js';

export const findNearestPrecedents = async (
  request: PrecedentSearchRequest
): Promise<PrecedentsApiResponse> => {
  try {
    const response = await apiClient.post<PrecedentsApiResponse>(
      '/precedents',
      { query_request: request },
    );
    return response.data;
  } catch (error: any) {
    console.error('Error fetching precedents:', error);
    throw new Error(error.response?.data?.detail || error.message || 'Failed to fetch precedents.');
  }
}; 