import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1', // Ensure this matches your backend API prefix
  headers: {
    'Content-Type': 'application/json',
  },
});

export default apiClient; 