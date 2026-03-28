'use client';
import { useState, useEffect } from 'react';
import { useAccounts, useRecommendations } from '@/lib/hooks';
import { api } from '@/lib/api';
import { Lightbulb, Check, X } from 'lucide-react';
import { mutate } from 'swr';

const typeColors: Record<string, string> = {
  content_idea: 'bg-sage/20 text-sage',
  timing: 'bg-blue-900/40 text-blue-300',
  hashtag: 'bg-green-900/40 text-green-300',
  format: 'bg-dun/20 text-dun',
  engagement: 'bg-pink-900/40 text-pink-300',
  remix: 'bg-cyan-900/40 text-cyan-300',
};

export default function RecommendationsPage() {
  const { data: accounts } = useAccounts();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [tab, setTab] = useState<'pending' | 'accepted' | 'dismissed'>('pending');

  useEffect(() => {
    if (accounts?.length && !selectedAccount) {
      setSelectedAccount(accounts[0].id);
    }
  }, [accounts, selectedAccount]);

  const { data: recs, isLoading } = useRecommendations(selectedAccount);
  const filtered = recs?.filter((r: any) => r.status === tab) || [];

  async function handleAction(id: string, status: string) {
    await api.updateRecommendation(id, status);
    mutate(`recs-${selectedAccount}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2 text-bone">
          <Lightbulb className="w-6 h-6 text-dun" />
          Recommendations
        </h1>
        {accounts?.length > 1 && (
          <select
            value={selectedAccount || ''}
            onChange={e => setSelectedAccount(e.target.value)}
            className="bg-reseda/20 border border-reseda/30 rounded-lg px-3 py-2 text-sm text-bone"
          >
            {accounts.map((acc: any) => (
              <option key={acc.id} value={acc.id}>@{acc.username}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex gap-1 bg-reseda/20 p-1 rounded-lg w-fit">
        {(['pending', 'accepted', 'dismissed'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm transition-colors capitalize ${
              tab === t ? 'bg-ebony text-bone' : 'text-dun hover:text-bone'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-24 bg-reseda/20 rounded-xl animate-pulse" />)}</div>
      ) : !filtered.length ? (
        <div className="text-center py-20 text-dun/60">No {tab} recommendations.</div>
      ) : (
        <div className="space-y-3">
          {filtered.map((rec: any) => (
            <div key={rec.id} className="bg-reseda/20 border border-reseda/30 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${typeColors[rec.recommendation_type] || 'bg-reseda/30 text-dun'}`}>
                      {rec.recommendation_type}
                    </span>
                    <span className="text-xs text-dun/50">Priority: {rec.priority}</span>
                  </div>
                  <h3 className="font-medium text-bone">{rec.title}</h3>
                </div>
                {tab === 'pending' && (
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => handleAction(rec.id, 'accepted')}
                      className="p-2 bg-sage/20 hover:bg-sage/40 text-sage rounded-lg transition-colors"
                      title="Accept"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleAction(rec.id, 'dismissed')}
                      className="p-2 bg-ebony/40 hover:bg-red-900/30 hover:text-red-400 text-dun rounded-lg transition-colors"
                      title="Dismiss"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
              <p className="text-sm text-dun">{rec.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
