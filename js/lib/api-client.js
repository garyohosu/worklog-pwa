export class ApiClient {
  constructor(baseUrl, getToken) {
    this.baseUrl = baseUrl;
    this.getToken = getToken; // () => string|null
  }

  async _request(method, path, body = null, params = null) {
    const url = new URL(path, this.baseUrl);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== null && v !== undefined) url.searchParams.set(k, v);
      }
    }
    const token = this.getToken ? this.getToken() : null;
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const init = { method, headers };
    if (body !== null) init.body = JSON.stringify(body);
    const res = await fetch(url.toString(), init);
    const json = await res.json();
    if (!res.ok) throw { status: res.status, ...json };
    return json;
  }

  get(path, params) { return this._request('GET', path, null, params); }
  post(path, body) { return this._request('POST', path, body); }
  put(path, body) { return this._request('PUT', path, body); }
  delete(path, params) { return this._request('DELETE', path, null, params); }

  // Auth
  register(data) { return this.post('/api/register.cgi', data); }
  login(data) { return this.post('/api/login.cgi', data); }
  logout() { return this.post('/api/logout.cgi', {}); }
  sessionCheck() { return this.get('/api/session_check.cgi'); }
  changePassword(data) { return this.post('/api/change_password.cgi', data); }

  // WorkLog
  listWorklogs(params) { return this.get('/api/worklog_api.cgi', { action: 'list', ...params }); }
  getWorklog(log_uuid) { return this.get('/api/worklog_api.cgi', { action: 'detail', log_uuid }); }
  createWorklog(data) { return this.post('/api/worklog_api.cgi?action=create', data); }
  updateWorklog(data) { return this.put('/api/worklog_api.cgi?action=update', data); }
  deleteWorklog(log_uuid) { return this.delete('/api/worklog_api.cgi', { action: 'delete', log_uuid }); }
  syncPush(items) { return this.post('/api/worklog_api.cgi?action=sync_push', { items }); }
  syncPull(since_token) { return this.get('/api/worklog_api.cgi', { action: 'sync_pull', since_token }); }

  // Equipment
  listEquipment() { return this.get('/api/equipment_api.cgi', { action: 'list' }); }
  searchEquipment(q) { return this.get('/api/equipment_api.cgi', { action: 'search', q }); }
  getByQr(qr_value) { return this.get('/api/equipment_api.cgi', { action: 'by_qr', qr_value }); }
  equipmentSyncPull(since_token) { return this.get('/api/equipment_api.cgi', { action: 'sync_pull', since_token }); }

  // Admin
  adminUserList() { return this.get('/api/admin_api.cgi', { action: 'user_list' }); }
  adminDashboard() { return this.get('/api/admin_api.cgi', { action: 'dashboard' }); }
  adminSetActive(data) { return this.put('/api/admin_api.cgi?action=set_active', data); }
  adminSetRole(data) { return this.put('/api/admin_api.cgi?action=set_role', data); }
  adminResetPassword(login_id) { return this.post('/api/admin_api.cgi?action=reset_password', { login_id }); }
}
