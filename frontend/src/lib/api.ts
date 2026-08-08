export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const getAuthToken = (): string => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('synex_access_token') || 'synex_developer_secret_token'
  }
  return 'synex_developer_secret_token'
}

export const setAuthToken = (token: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('synex_access_token', token)
  }
}

export const fetchWithAuth = (url: string, options: RequestInit = {}): Promise<Response> => {
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${getAuthToken()}`,
  }
  return fetch(url, { ...options, headers })
}
