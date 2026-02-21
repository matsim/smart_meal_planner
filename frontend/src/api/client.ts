import axios from 'axios';

// Configure Axios instance. 
// Thanks to Vite's proxy config, requests to /api/v1 are proxied to the FastAPI server at 127.0.0.1:8000
const apiClient = axios.create({
    baseURL: '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

export default apiClient;
