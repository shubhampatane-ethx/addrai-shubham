/**
 * Authentication Service
 * Utility functions for auth management
 */
import axios from 'axios';

const authService = {
  /**
   * Check if user is authenticated
   */
  isAuthenticated: () => {
    const token = localStorage.getItem('token');
    return !!token;
  },

  /**
   * Get current user from localStorage
   */
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch (e) {
        return null;
      }
    }
    return null;
  },

  /**
   * Check if current user is admin
   */
  isAdmin: () => {
    const user = authService.getCurrentUser();
    return user && user.role === 'admin';
  },

  /**
   * Get auth token
   */
  getToken: () => {
    return localStorage.getItem('token');
  },

  /**
   * Logout user
   */
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    delete axios.defaults.headers.common['Authorization'];
    window.location.href = '/login';
  },

  /**
   * Setup axios interceptor for auth token
   */
  setupAxiosInterceptor: () => {
    const token = authService.getToken();
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }

    // Add response interceptor to handle 401
    axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          authService.logout();
        }
        return Promise.reject(error);
      }
    );
  }
};

export default authService;
