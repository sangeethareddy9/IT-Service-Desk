let csrf = '';
export async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.body && !(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (options.method && options.method !== 'GET') headers['X-CSRF-Token'] = csrf;
  const response = await fetch('/api' + path, { ...options, headers, credentials: 'same-origin' });
  const result = await response.json().catch(() => ({ error: 'The server returned an unexpected response.' }));
  if (result.csrf) csrf = result.csrf;
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') window.dispatchEvent(new Event('session-expired'));
    throw new Error(result.error || 'Request failed.');
  }
  return result;
}
export const post = (path, body = {}) => api(path, { method: 'POST', body: JSON.stringify(body) });
export const patch = (path, body) => api(path, { method: 'PATCH', body: JSON.stringify(body) });
