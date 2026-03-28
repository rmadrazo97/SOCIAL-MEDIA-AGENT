'use client';
import { useState, useEffect } from 'react';
import { useAccounts, usePosts } from '@/lib/hooks';
import { Eye, Heart, MessageCircle, Share2, Instagram, Music2 } from 'lucide-react';
import Link from 'next/link';

export default function PostsPage() {
  const { data: accounts } = useAccounts();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);

  useEffect(() => {
    if (accounts?.length && !selectedAccount) {
      setSelectedAccount(accounts[0].id);
    }
  }, [accounts, selectedAccount]);

  const { data: posts, isLoading } = usePosts(selectedAccount);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-bone">Posts</h1>
        {accounts?.length > 1 && (
          <select
            value={selectedAccount || ''}
            onChange={(e) => setSelectedAccount(e.target.value)}
            className="bg-reseda/20 border border-reseda/30 rounded-lg px-3 py-2 text-sm text-bone"
          >
            {accounts.map((acc: any) => (
              <option key={acc.id} value={acc.id}>@{acc.username} ({acc.platform})</option>
            ))}
          </select>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-20 bg-reseda/20 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : !posts?.length ? (
        <div className="text-center py-20 text-dun/60">
          <p>No posts found. Import data via CSV or connect a platform.</p>
        </div>
      ) : (
        <div className="bg-reseda/20 border border-reseda/30 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-reseda/30 text-dun text-left">
                <th className="px-4 py-3 font-medium">Post</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium text-right">Views</th>
                <th className="px-4 py-3 font-medium text-right">Likes</th>
                <th className="px-4 py-3 font-medium text-right">Comments</th>
                <th className="px-4 py-3 font-medium text-right">Shares</th>
                <th className="px-4 py-3 font-medium text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {posts.map((post: any) => {
                const m = post.latest_metrics;
                const score = m?.performance_score;
                let scoreColor = 'text-dun/50';
                if (score >= 90) scoreColor = 'text-purple-400';
                else if (score >= 75) scoreColor = 'text-green-400';
                else if (score >= 50) scoreColor = 'text-yellow-400';
                else if (score >= 25) scoreColor = 'text-orange-400';
                else if (score !== null && score !== undefined) scoreColor = 'text-red-400';

                return (
                  <tr key={post.id} className="border-b border-reseda/20 hover:bg-ebony/30 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/posts/${post.id}`} className="hover:text-sage transition-colors">
                        <div className="flex items-center gap-2">
                          {post.platform === 'instagram' ? <Instagram className="w-3 h-3 text-pink-400" /> : <Music2 className="w-3 h-3 text-cyan-400" />}
                          <span className="truncate max-w-xs text-bone">{post.caption || 'No caption'}</span>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-dun">{post.post_type}</td>
                    <td className="px-4 py-3 text-dun">{new Date(post.posted_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-right text-bone">{m?.views?.toLocaleString() || '-'}</td>
                    <td className="px-4 py-3 text-right text-bone">{m?.likes?.toLocaleString() || '-'}</td>
                    <td className="px-4 py-3 text-right text-bone">{m?.comments?.toLocaleString() || '-'}</td>
                    <td className="px-4 py-3 text-right text-bone">{m?.shares?.toLocaleString() || '-'}</td>
                    <td className={`px-4 py-3 text-right font-medium ${scoreColor}`}>
                      {score !== null && score !== undefined ? score : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
