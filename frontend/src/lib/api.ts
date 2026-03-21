import axios from "axios";
import { getToken } from "./auth";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "",
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status >= 500) {
      console.error(
        `[API] Server error ${error.response.status}:`,
        error.response.config?.method?.toUpperCase(),
        error.response.config?.url,
        error.response.data
      );
    }
    return Promise.reject(error);
  }
);

export default api;
