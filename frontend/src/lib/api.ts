const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

class ApiClient {
  private password: string = '';

  setPassword(pw: string) {
    this.password = pw;
    if (typeof window !== 'undefined') {
      localStorage.setItem('app_password', pw);
    }
  }

  getPassword(): string {
    if (this.password) return this.password;
    if (typeof window !== 'undefined') {
      this.password = localStorage.getItem('app_password') || '';
    }
    return this.password;
  }

  isAuthenticated(): boolean {
    return !!this.getPassword();
  }

  logout() {
    this.password = '';
    if (typeof window !== 'undefined') {
      localStorage.removeItem('app_password');
    }
  }

  private async fetch(path: string, options: RequestInit = {}): Promise<any> {
    const headers: Record<string, string> = {
      'x-app-password': this.getPassword(),
      ...(options.headers as Record<string, string> || {}),
    };
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401) {
      this.logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error('Unauthorized');
    }

    if (res.status === 204) return null;

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || 'Request failed');
    }

    return res.json();
  }

  // Auth
  async login(password: string): Promise<boolean> {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      this.setPassword(password);
      return true;
    }
    return false;
  }

  // Accounts
  async getAccounts() { return this.fetch('/api/accounts'); }
  async createAccount(data: { platform: string; username: string }) {
    return this.fetch('/api/accounts', { method: 'POST', body: JSON.stringify(data) });
  }
  async deleteAccount(id: string) {
    return this.fetch(`/api/accounts/${id}`, { method: 'DELETE' });
  }
  async syncAccount(id: string) {
    return this.fetch(`/api/accounts/${id}/sync`, { method: 'POST' });
  }
  async syncAll() {
    return this.fetch('/api/sync/all', { method: 'POST' });
  }
  async syncStatus() {
    return this.fetch('/api/sync/status');
  }

  // Posts
  async getPosts(accountId: string, params?: { platform?: string; post_type?: string; limit?: number }) {
    const q = new URLSearchParams();
    if (params?.platform) q.set('platform', params.platform);
    if (params?.post_type) q.set('post_type', params.post_type);
    if (params?.limit) q.set('limit', params.limit.toString());
    return this.fetch(`/api/accounts/${accountId}/posts?${q}`);
  }
  async getPost(id: string) { return this.fetch(`/api/posts/${id}`); }
  async createPost(data: any) {
    return this.fetch('/api/posts', { method: 'POST', body: JSON.stringify(data) });
  }
  async deletePost(id: string) {
    return this.fetch(`/api/posts/${id}`, { method: 'DELETE' });
  }

  // Metrics
  async getPostMetrics(postId: string) { return this.fetch(`/api/posts/${postId}/metrics`); }
  async createPostMetric(postId: string, data: any) {
    return this.fetch(`/api/posts/${postId}/metrics`, { method: 'POST', body: JSON.stringify({ ...data, post_id: postId }) });
  }
  async getAccountMetrics(accountId: string, days = 7) {
    return this.fetch(`/api/accounts/${accountId}/metrics?days=${days}`);
  }
  async getBaseline(accountId: string) { return this.fetch(`/api/accounts/${accountId}/baseline`); }

  // Insights
  async getPostDiagnostic(postId: string) { return this.fetch(`/api/posts/${postId}/diagnostic`); }
  async generateDiagnostic(postId: string) {
    return this.fetch(`/api/posts/${postId}/diagnostic`, { method: 'POST' });
  }

  // Daily Briefs
  async getTodayBrief(accountId: string) { return this.fetch(`/api/accounts/${accountId}/brief`); }
  async generateBrief(accountId: string) {
    return this.fetch(`/api/accounts/${accountId}/brief`, { method: 'POST' });
  }
  async getBriefs(accountId: string) { return this.fetch(`/api/accounts/${accountId}/briefs`); }

  // Recommendations
  async getRecommendations(accountId: string, status?: string) {
    const q = status ? `?status=${status}` : '';
    return this.fetch(`/api/accounts/${accountId}/recommendations${q}`);
  }
  async updateRecommendation(id: string, status: string) {
    return this.fetch(`/api/recommendations/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
  }

  // Remix
  async generateRemix(postId: string, remixType = 'carousel') {
    return this.fetch(`/api/posts/${postId}/remix`, { method: 'POST', body: JSON.stringify({ remix_type: remixType }) });
  }

  // CSV Import
  async importCsv(accountId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.fetch(`/api/accounts/${accountId}/import`, { method: 'POST', body: formData });
  }
}

export const api = new ApiClient();
