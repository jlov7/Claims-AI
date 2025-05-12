import apiClient from './apiClient.ts';
import axios from 'axios';

export interface HealthStatus { // Renamed and Exported
  status: string;
  message?: string; 
  healthy?: boolean; // Added to align with HomePage usage
}

export const getBackendHealth = async (): Promise<HealthStatus> => {
  try {
    const response = await axios.get<{ status: string, message?: string }>('http://localhost:8000/health');
    // Assuming backend returns { "status": "Healthy", "message": "Backend is running" }
    // or { "status": "Unhealthy", "message": "Something is wrong" }
    // We can add a healthy boolean for easier consumption in frontend
    return {
      ...response.data,
      healthy: response.data.status?.toLowerCase().includes('healthy') || response.data.status?.toLowerCase().includes('ok')
    };
  } catch (error) {
    console.error('Error fetching backend health:', error);
    return { status: 'Error', message: 'Error connecting to backend', healthy: false };
  }
}; 