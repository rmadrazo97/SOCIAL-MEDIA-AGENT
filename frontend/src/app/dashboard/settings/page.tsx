'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Settings, LogOut } from 'lucide-react';

export default function SettingsPage() {
  const router = useRouter();
  const [apiUrl] = useState(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001');

  function handleLogout() {
    api.logout();
    router.push('/login');
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold flex items-center gap-2 text-bone">
        <Settings className="w-6 h-6 text-dun" />
        Settings
      </h1>

      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6 space-y-4">
        <h2 className="font-medium text-bone">Connection</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-dun">API URL</span>
            <span className="text-bone font-mono text-xs">{apiUrl}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dun">Status</span>
            <span className="text-sage">Connected</span>
          </div>
        </div>
      </div>

      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6 space-y-4">
        <h2 className="font-medium text-bone">Session</h2>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded-lg text-sm transition-colors"
        >
          <LogOut className="w-4 h-4" /> Logout
        </button>
      </div>

      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6 space-y-4">
        <h2 className="font-medium text-bone">About</h2>
        <div className="text-sm text-dun space-y-1">
          <p>Social Media Command Center v1.0.0</p>
          <p>AI-powered analytics for Instagram & TikTok creators.</p>
          <p>Open source project.</p>
        </div>
      </div>
    </div>
  );
}
