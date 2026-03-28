'use client';
import { useState, useEffect } from 'react';
import { useAccounts, usePosts, useAccountMetrics, useDailyBrief, useRecommendations } from '@/lib/hooks';
import { api } from '@/lib/api';
import {
  Eye, Heart, MessageCircle, Share2, Bookmark, TrendingUp,
  Sparkles, RefreshCw, ArrowRight, Instagram, Music2, Lightbulb
} from 'lucide-react';
import Link from 'next/link';

function PlatformIcon({ platform }: { platform: string }) {
  if (platform === 'instagram') return <Instagram className="w-4 h-4 text-pink-400" />;
  if (platform === 'tiktok') return <Music2 className="w-4 h-4 text-cyan-400" />;
  return null;
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: number | string; icon: any }) {
  return (
    <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-4">
      <div className="flex items-center gap-2 text-dun text-sm mb-1">
        <Icon className="w-4 h-4" />
        {label}
      </div>
      <div className="text-2xl font-bold text-bone">{typeof value === 'number' ? value.toLocaleString() : value}</div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null || score === undefined) return <span className="text-dun/50 text-xs">N/A</span>;
  let color = 'text-dun bg-reseda/30';
  if (score >= 90) color = 'text-purple-300 bg-purple-900/40';
  else if (score >= 75) color = 'text-green-300 bg-green-900/40';
  else if (score >= 50) color = 'text-yellow-300 bg-yellow-900/40';
  else if (score >= 25) color = 'text-orange-300 bg-orange-900/40';
  else color = 'text-red-300 bg-red-900/40';
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>{score}</span>;
}

export default function DashboardPage() {
  const { data: accounts, isLoading: accLoading } = useAccounts();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);

  useEffect(() => {
    if (accounts?.length && !selectedAccount) {
      setSelectedAccount(accounts[0].id);
    }
  }, [accounts, selectedAccount]);

  const { data: posts } = usePosts(selectedAccount);
  const { data: metrics } = useAccountMetrics(selectedAccount);
  const { data: brief } = useDailyBrief(selectedAccount);
  const { data: recs } = useRecommendations(selectedAccount);
  const [generatingBrief, setGeneratingBrief] = useState(false);

  async function handleGenerateBrief() {
    if (!selectedAccount) return;
    setGeneratingBrief(true);
    try {
      await api.generateBrief(selectedAccount);
      window.location.reload();
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingBrief(false);
    }
  }

  if (accLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-32 bg-reseda/20 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (!accounts?.length) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <Sparkles className="w-12 h-12 text-sage mb-4" />
        <h2 className="text-xl font-bold mb-2 text-bone">Welcome to SM Agent</h2>
        <p className="text-dun mb-6">Connect your first social media account to get started.</p>
        <Link href="/dashboard/accounts" className="px-6 py-3 bg-sage hover:bg-sage/80 rounded-xl font-medium text-ebony transition-colors">
          Connect Account
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Account selector */}
      {accounts.length > 1 && (
        <div className="flex gap-2">
          {accounts.map((acc: any) => (
            <button
              key={acc.id}
              onClick={() => setSelectedAccount(acc.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                selectedAccount === acc.id ? 'bg-sage/20 text-sage border border-sage/30' : 'bg-reseda/20 text-dun border border-reseda/30 hover:border-reseda/60'
              }`}
            >
              <PlatformIcon platform={acc.platform} />
              @{acc.username}
            </button>
          ))}
        </div>
      )}

      {/* Metrics row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <MetricCard label="Views" value={metrics?.total_views || 0} icon={Eye} />
        <MetricCard label="Likes" value={metrics?.total_likes || 0} icon={Heart} />
        <MetricCard label="Comments" value={metrics?.total_comments || 0} icon={MessageCircle} />
        <MetricCard label="Shares" value={metrics?.total_shares || 0} icon={Share2} />
        <MetricCard label="Saves" value={metrics?.total_saves || 0} icon={Bookmark} />
        <MetricCard label="Posts" value={metrics?.post_count || 0} icon={TrendingUp} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Daily Brief */}
        <div className="lg:col-span-2 bg-reseda/20 border border-reseda/30 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2 text-bone">
              <Sparkles className="w-5 h-5 text-sage" />
              Daily Brief
            </h2>
            <button
              onClick={handleGenerateBrief}
              disabled={generatingBrief}
              className="flex items-center gap-1 text-sm text-sage hover:text-sage/80 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${generatingBrief ? 'animate-spin' : ''}`} />
              {brief ? 'Refresh' : 'Generate'}
            </button>
          </div>
          {brief ? (
            <div className="prose prose-invert prose-sm max-w-none text-dun">
              <div className="whitespace-pre-wrap">{brief.content}</div>
            </div>
          ) : (
            <p className="text-dun/60">No brief for today. Click Generate to create one.</p>
          )}
        </div>

        {/* Recommendations sidebar */}
        <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold flex items-center gap-2 text-bone">
              <Lightbulb className="w-5 h-5 text-dun" />
              Recommendations
            </h2>
            <Link href="/dashboard/recommendations" className="text-sm text-sage hover:text-sage/80">
              View all
            </Link>
          </div>
          {recs?.length ? (
            <div className="space-y-3">
              {recs.slice(0, 3).map((rec: any) => (
                <div key={rec.id} className="p-3 bg-ebony/40 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-sage/20 text-sage">{rec.recommendation_type}</span>
                    <span className="text-xs text-dun/50">P{rec.priority}</span>
                  </div>
                  <p className="text-sm font-medium text-bone">{rec.title}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-dun/60 text-sm">No recommendations yet.</p>
          )}
        </div>
      </div>

      {/* Recent Posts */}
      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-bone">Recent Posts</h2>
          <Link href="/dashboard/posts" className="flex items-center gap-1 text-sm text-sage hover:text-sage/80">
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        {posts?.length ? (
          <div className="space-y-3">
            {posts.slice(0, 5).map((post: any) => (
              <Link
                key={post.id}
                href={`/dashboard/posts/${post.id}`}
                className="flex items-center gap-4 p-3 bg-ebony/40 rounded-lg hover:bg-ebony/60 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <PlatformIcon platform={post.platform} />
                    <span className="text-xs text-dun/60">{post.post_type}</span>
                    <span className="text-xs text-dun/40">{new Date(post.posted_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm truncate text-bone">{post.caption || 'No caption'}</p>
                </div>
                <div className="flex items-center gap-4 text-sm text-dun shrink-0">
                  {post.latest_metrics && (
                    <>
                      <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {post.latest_metrics.views.toLocaleString()}</span>
                      <span className="flex items-center gap-1"><Heart className="w-3 h-3" /> {post.latest_metrics.likes.toLocaleString()}</span>
                      <ScoreBadge score={post.latest_metrics.performance_score} />
                    </>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-dun/60 text-sm">No posts yet. Import data or connect an account.</p>
        )}
      </div>
    </div>
  );
}
