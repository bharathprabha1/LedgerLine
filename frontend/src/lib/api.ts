
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

// Attach the current session's JWT to authenticated requests.
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('ledgerline_access_token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

// Handle expired or invalid authentication.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('ledgerline_access_token')
      sessionStorage.removeItem('ledgerline_user')
    }

    return Promise.reject(error)
  },
)

export default api
