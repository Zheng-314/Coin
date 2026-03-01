const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5001'

export const apiUrl = (path) => `${API_BASE_URL}${path}`

export default API_BASE_URL
