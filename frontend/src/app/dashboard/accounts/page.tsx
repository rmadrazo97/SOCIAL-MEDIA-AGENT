'use client';
import { useState } from 'react';
import { useAccounts } from '@/lib/hooks';
import { api } from '@/lib/api';
import { Instagram, Music2, Plus, Trash2, Upload, X, RefreshCw, Zap } from 'lucide-react';
import { mutate } from 'swr';

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts();
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState<string | null>(null);
  const [form, setForm] = useState({ platform: 'instagram', username: '' });
  const [saving, setSaving] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [syncing, setSyncing] = useState<Record<string, boolean>>({});
  const [syncingAll, setSyncingAll] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const acc = await api.createAccount(form);
      setShowAdd(false);
      setForm({ platform: 'instagram', username: '' });
      mutate('accounts');
      // Auto-sync the new account
      try {
        await api.syncAccount(acc.id);
      } catch {}
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Disconnect this account? All data will be removed.')) return;
    await api.deleteAccount(id);
    mutate('accounts');
  }

  async function handleSync(id: string) {
    setSyncing(prev => ({ ...prev, [id]: true }));
    try {
      await api.syncAccount(id);
      // Wait a bit for background task to start, then refresh
      setTimeout(() => mutate('accounts'), 3000);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setSyncing(prev => ({ ...prev, [id]: false })), 5000);
    }
  }

  async function handleSyncAll() {
    setSyncingAll(true);
    try {
      await api.syncAll();
      setTimeout(() => mutate('accounts'), 5000);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setSyncingAll(false), 8000);
    }
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.files?.length || !showImport) return;
    try {
      const result = await api.importCsv(showImport, e.target.files[0]);
      setImportResult(result);
      mutate('accounts');
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-bone">Connected Accounts</h1>
        <div className="flex gap-2">
          {accounts?.length > 0 && (
            <button
              onClick={handleSyncAll}
              disabled={syncingAll}
              className="flex items-center gap-2 px-4 py-2 bg-reseda/30 hover:bg-reseda/50 border border-reseda/40 rounded-lg text-sm text-bone transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${syncingAll ? 'animate-spin' : ''}`} />
              {syncingAll ? 'Syncing...' : 'Sync All'}
            </button>
          )}
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-sage hover:bg-sage/80 rounded-lg text-sm text-ebony font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Account
          </button>
        </div>
      </div>

      {/* Info banner */}
      <div className="bg-sage/10 border border-sage/20 rounded-xl p-4 flex items-start gap-3">
        <Zap className="w-5 h-5 text-sage shrink-0 mt-0.5" />
        <div className="text-sm text-dun">
          <p className="font-medium text-bone mb-1">How it works</p>
          <p>Add your Instagram or TikTok username. The system automatically scrapes public profile data and post metrics every 2 hours. You can also trigger a manual sync anytime.</p>
          <p className="mt-1 text-dun/60">Note: Only public profiles can be scraped. Private accounts require CSV import.</p>
        </div>
      </div>

      {/* Add account modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAdd(false)}>
          <div className="bg-ebony border border-reseda/30 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-bone">Add Account</h2>
              <button onClick={() => setShowAdd(false)}><X className="w-5 h-5 text-dun" /></button>
            </div>
            <form onSubmit={handleAdd} className="space-y-4">
              <div>
                <label className="text-sm text-dun mb-1 block">Platform</label>
                <select
                  value={form.platform}
                  onChange={e => setForm({ ...form, platform: e.target.value })}
                  className="w-full bg-reseda/20 border border-reseda/30 rounded-lg px-3 py-2 text-bone"
                >
                  <option value="instagram">Instagram</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-dun mb-1 block">Username (without @)</label>
                <input
                  value={form.username}
                  onChange={e => setForm({ ...form, username: e.target.value.replace('@', '') })}
                  placeholder="username"
                  className="w-full bg-reseda/20 border border-reseda/30 rounded-lg px-3 py-2 text-bone placeholder:text-dun/50"
                  required
                />
              </div>
              <p className="text-xs text-dun/60">
                The profile must be public. After adding, the system will automatically scrape posts and metrics.
              </p>
              <button
                type="submit"
                disabled={saving || !form.username}
                className="w-full py-2 bg-sage hover:bg-sage/80 disabled:opacity-50 rounded-lg font-medium text-ebony transition-colors"
              >
                {saving ? 'Adding & Syncing...' : 'Add Account'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Import modal */}
      {showImport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => { setShowImport(null); setImportResult(null); }}>
          <div className="bg-ebony border border-reseda/30 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-bone">Import CSV Data</h2>
              <button onClick={() => { setShowImport(null); setImportResult(null); }}><X className="w-5 h-5 text-dun" /></button>
            </div>
            <p className="text-sm text-dun mb-4">
              CSV format: post_url, caption, posted_at, post_type, views, likes, comments, shares, saves, reach
            </p>
            <input type="file" accept=".csv" onChange={handleImport} className="w-full text-sm text-bone" />
            {importResult && (
              <div className="mt-4 p-3 bg-reseda/20 rounded-lg text-sm">
                <p className="text-sage">Created: {importResult.created}</p>
                <p className="text-blue-400">Updated: {importResult.updated}</p>
                {importResult.errors?.length > 0 && (
                  <div className="text-red-400 mt-2">
                    {importResult.errors.map((e: string, i: number) => <p key={i}>{e}</p>)}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Accounts list */}
      {isLoading ? (
        <div className="space-y-3">{[...Array(2)].map((_, i) => <div key={i} className="h-28 bg-reseda/20 rounded-xl animate-pulse" />)}</div>
      ) : !accounts?.length ? (
        <div className="text-center py-20 text-dun/60">No accounts connected. Click &quot;Add Account&quot; to get started.</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {accounts.map((acc: any) => (
            <div key={acc.id} className="bg-reseda/20 border border-reseda/30 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  {acc.platform === 'instagram' ? <Instagram className="w-6 h-6 text-pink-400" /> : <Music2 className="w-6 h-6 text-cyan-400" />}
                  <div>
                    <p className="font-medium text-bone">@{acc.username}</p>
                    <p className="text-xs text-dun/60 capitalize">{acc.platform}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  acc.status === 'active' ? 'bg-sage/20 text-sage' :
                  acc.status === 'expired' ? 'bg-yellow-900/40 text-yellow-300' :
                  'bg-red-900/40 text-red-300'
                }`}>
                  {acc.status}
                </span>
              </div>
              {acc.follower_count && (
                <p className="text-sm text-dun mb-3">{acc.follower_count.toLocaleString()} followers</p>
              )}
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => handleSync(acc.id)}
                  disabled={syncing[acc.id]}
                  className="flex items-center gap-1 px-3 py-1.5 bg-sage/20 hover:bg-sage/30 border border-sage/30 rounded-lg text-xs text-sage transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 ${syncing[acc.id] ? 'animate-spin' : ''}`} />
                  {syncing[acc.id] ? 'Syncing...' : 'Sync Now'}
                </button>
                <button
                  onClick={() => setShowImport(acc.id)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-ebony/40 hover:bg-ebony/60 border border-reseda/30 rounded-lg text-xs text-bone transition-colors"
                >
                  <Upload className="w-3 h-3" /> Import CSV
                </button>
                <button
                  onClick={() => handleDelete(acc.id)}
                  className="flex items-center gap-1 px-3 py-1.5 bg-ebony/40 hover:bg-red-900/30 hover:text-red-300 border border-reseda/30 rounded-lg text-xs text-dun transition-colors ml-auto"
                >
                  <Trash2 className="w-3 h-3" /> Disconnect
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
