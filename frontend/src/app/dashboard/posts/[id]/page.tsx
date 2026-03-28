'use client';
import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { usePost, usePostMetrics } from '@/lib/hooks';
import { api } from '@/lib/api';
import {
  Eye, Heart, MessageCircle, Share2, Bookmark, ArrowLeft,
  Sparkles, RefreshCw, Wand2, Instagram, Music2, ExternalLink
} from 'lucide-react';

export default function PostDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { data: post, isLoading } = usePost(id as string);
  const { data: metricHistory } = usePostMetrics(id as string);
  const [diagnostic, setDiagnostic] = useState<any>(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [remixes, setRemixes] = useState<any[]>([]);
  const [remixLoading, setRemixLoading] = useState(false);

  async function loadDiagnostic() {
    setDiagLoading(true);
    try {
      const d = await api.getPostDiagnostic(id as string);
      if (d) {
        setDiagnostic(d);
      } else {
        const nd = await api.generateDiagnostic(id as string);
        setDiagnostic(nd);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setDiagLoading(false);
    }
  }

  async function handleGenerateRemix(type: string) {
    setRemixLoading(true);
    try {
      const r = await api.generateRemix(id as string, type);
      setRemixes(r);
    } catch (e) {
      console.error(e);
    } finally {
      setRemixLoading(false);
    }
  }

  if (isLoading) {
    return <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-32 bg-reseda/20 rounded-xl animate-pulse" />)}</div>;
  }

  if (!post) {
    return <div className="text-center py-20 text-dun/60">Post not found.</div>;
  }

  const m = post.latest_metrics;

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="flex items-center gap-2 text-sm text-dun hover:text-bone">
        <ArrowLeft className="w-4 h-4" /> Back
      </button>

      {/* Post header */}
      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          {post.platform === 'instagram' ? <Instagram className="w-5 h-5 text-pink-400" /> : <Music2 className="w-5 h-5 text-cyan-400" />}
          <span className="text-sm px-2 py-0.5 rounded-full bg-ebony/40 text-dun">{post.post_type}</span>
          <span className="text-sm text-dun/60">{new Date(post.posted_at).toLocaleString()}</span>
          {post.permalink && (
            <a href={post.permalink} target="_blank" rel="noopener" className="ml-auto text-dun/60 hover:text-bone">
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
        <p className="text-bone">{post.caption || 'No caption'}</p>
      </div>

      {/* Metrics */}
      {m && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          {[
            { label: 'Views', value: m.views, icon: Eye },
            { label: 'Likes', value: m.likes, icon: Heart },
            { label: 'Comments', value: m.comments, icon: MessageCircle },
            { label: 'Shares', value: m.shares, icon: Share2 },
            { label: 'Saves', value: m.saves, icon: Bookmark },
            { label: 'Engagement', value: `${(m.engagement_rate * 100).toFixed(1)}%`, icon: Sparkles },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-reseda/20 border border-reseda/30 rounded-xl p-4">
              <div className="flex items-center gap-2 text-dun text-xs mb-1">
                <Icon className="w-3 h-3" />
                {label}
              </div>
              <div className="text-xl font-bold text-bone">{typeof value === 'number' ? value.toLocaleString() : value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Metrics History */}
      {metricHistory?.length > 1 && (
        <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
          <h3 className="text-lg font-bold mb-4 text-bone">Metrics Over Time</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-reseda/30 text-dun text-left">
                  <th className="px-3 py-2">Snapshot</th>
                  <th className="px-3 py-2 text-right">Views</th>
                  <th className="px-3 py-2 text-right">Likes</th>
                  <th className="px-3 py-2 text-right">Comments</th>
                  <th className="px-3 py-2 text-right">Shares</th>
                </tr>
              </thead>
              <tbody>
                {metricHistory.map((snap: any) => (
                  <tr key={snap.id} className="border-b border-reseda/20">
                    <td className="px-3 py-2 text-dun">{new Date(snap.snapshot_at).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-bone">{snap.views.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-bone">{snap.likes.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-bone">{snap.comments.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right text-bone">{snap.shares.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI Diagnostic */}
      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2 text-bone">
            <Sparkles className="w-5 h-5 text-sage" />
            AI Diagnostic
          </h3>
          <button
            onClick={loadDiagnostic}
            disabled={diagLoading}
            className="flex items-center gap-1 text-sm text-sage hover:text-sage/80 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${diagLoading ? 'animate-spin' : ''}`} />
            {diagnostic ? 'Regenerate' : 'Generate'}
          </button>
        </div>
        {diagnostic ? (
          <div className="space-y-4">
            <p className="text-bone">{diagnostic.content}</p>
            {diagnostic.metadata_json?.key_factors?.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-dun">Key Factors</h4>
                {diagnostic.metadata_json.key_factors.map((f: any, i: number) => (
                  <div key={i} className="p-3 bg-ebony/40 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-bone">{f.factor}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${f.impact === 'positive' ? 'bg-sage/20 text-sage' : 'bg-red-900/40 text-red-300'}`}>
                        {f.impact}
                      </span>
                    </div>
                    <p className="text-sm text-dun">{f.explanation}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <p className="text-dun/60 text-sm">Click Generate to get an AI analysis of this post.</p>
        )}
      </div>

      {/* Remix */}
      <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
        <h3 className="text-lg font-bold flex items-center gap-2 mb-4 text-bone">
          <Wand2 className="w-5 h-5 text-dun" />
          Remix Generator
        </h3>
        <div className="flex gap-2 mb-4">
          {['carousel', 'reel_script', 'story_series'].map(type => (
            <button
              key={type}
              onClick={() => handleGenerateRemix(type)}
              disabled={remixLoading}
              className="px-4 py-2 bg-ebony/40 hover:bg-ebony/60 border border-reseda/30 rounded-lg text-sm text-bone transition-colors disabled:opacity-50"
            >
              {remixLoading ? 'Generating...' : type.replace('_', ' ')}
            </button>
          ))}
        </div>
        {remixes.length > 0 && (
          <div className="space-y-3">
            {remixes.map((remix: any, i: number) => (
              <div key={i} className="p-4 bg-ebony/40 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-sage/20 text-sage">{remix.format}</span>
                </div>
                <pre className="text-sm whitespace-pre-wrap text-dun">{JSON.stringify(remix.content, null, 2)}</pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
