'use client';
import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { usePost, usePostMetrics, usePostComments } from '@/lib/hooks';
import { api } from '@/lib/api';
import {
  Eye, Heart, MessageCircle, Share2, Bookmark, ArrowLeft,
  Sparkles, RefreshCw, Wand2, Instagram, Music2, ExternalLink,
  ChevronLeft, ChevronRight, Play, Image as ImageIcon, ThumbsUp, Reply,
  Users, Target, TrendingUp, UserPlus, BarChart3
} from 'lucide-react';

function InsightsSection({ insight }: { insight: any }) {
  const nonFollowerPct = insight.reach_non_follower_pct ?? 0;
  const followerPct = insight.reach_follower_pct ?? 100;
  const discoveryLevel = nonFollowerPct >= 30 ? 'high' : nonFollowerPct >= 15 ? 'medium' : 'low';
  const discoveryColor = discoveryLevel === 'high' ? 'text-green-400' : discoveryLevel === 'medium' ? 'text-yellow-400' : 'text-red-400';

  // Find top impression source
  const sources = [
    { name: 'Home', value: insight.from_home },
    { name: 'Profile', value: insight.from_profile },
    { name: 'Hashtags', value: insight.from_hashtags },
    { name: 'Explore', value: insight.from_explore },
    { name: 'Other', value: insight.from_other },
  ];
  const totalSources = sources.reduce((s, x) => s + x.value, 0);

  return (
    <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
      <h3 className="text-lg font-bold flex items-center gap-2 mb-4 text-bone">
        <BarChart3 className="w-5 h-5 text-sage" />
        Instagram Insights
      </h3>

      {/* Top cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <div className="bg-ebony/40 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-dun text-xs mb-1">
            <Users className="w-3 h-3" /> Accounts Reached
          </div>
          <div className="text-xl font-bold text-bone">{insight.accounts_reached.toLocaleString()}</div>
        </div>
        <div className="bg-ebony/40 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-dun text-xs mb-1">
            <Eye className="w-3 h-3" /> Impressions
          </div>
          <div className="text-xl font-bold text-bone">{insight.impressions.toLocaleString()}</div>
        </div>
        <div className="bg-ebony/40 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-dun text-xs mb-1">
            <Target className="w-3 h-3" /> Interactions
          </div>
          <div className="text-xl font-bold text-bone">{insight.total_interactions.toLocaleString()}</div>
        </div>
        <div className="bg-ebony/40 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-dun text-xs mb-1">
            <TrendingUp className="w-3 h-3" /> Discovery
          </div>
          <div className={`text-xl font-bold ${discoveryColor}`}>
            {nonFollowerPct.toFixed(1)}%
          </div>
          <div className="text-xs text-dun/60">non-followers</div>
        </div>
      </div>

      {/* Reach breakdown */}
      {(insight.reach_follower_pct != null || insight.reach_non_follower_pct != null) && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-dun mb-2">Reach — Follower vs Non-Follower</h4>
          <div className="flex h-6 rounded-full overflow-hidden bg-ebony/40">
            <div
              className="bg-sage/70 flex items-center justify-center text-xs text-bone font-medium"
              style={{ width: `${followerPct}%` }}
            >
              {followerPct > 10 && `${followerPct.toFixed(0)}% followers`}
            </div>
            <div
              className="bg-pink-500/60 flex items-center justify-center text-xs text-bone font-medium"
              style={{ width: `${nonFollowerPct}%` }}
            >
              {nonFollowerPct > 10 && `${nonFollowerPct.toFixed(0)}% new`}
            </div>
          </div>
        </div>
      )}

      {/* Impression source breakdown */}
      {totalSources > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-medium text-dun mb-2">Impression Sources</h4>
          <div className="space-y-2">
            {sources.filter(s => s.value > 0).sort((a, b) => b.value - a.value).map(s => {
              const pct = (s.value / totalSources) * 100;
              return (
                <div key={s.name} className="flex items-center gap-3">
                  <span className="text-xs text-dun w-16">{s.name}</span>
                  <div className="flex-1 h-4 bg-ebony/40 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        s.name === 'Explore' ? 'bg-purple-500/70' :
                        s.name === 'Hashtags' ? 'bg-blue-500/70' :
                        s.name === 'Home' ? 'bg-sage/70' :
                        s.name === 'Profile' ? 'bg-dun/50' :
                        'bg-reseda/50'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-bone w-16 text-right">
                    {s.value.toLocaleString()} ({pct.toFixed(0)}%)
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Profile activity */}
      {(insight.profile_visits > 0 || insight.follows > 0) && (
        <div className="flex gap-4">
          {insight.profile_visits > 0 && (
            <div className="flex items-center gap-2 text-sm text-dun">
              <Users className="w-4 h-4 text-sage" />
              <span className="text-bone font-medium">{insight.profile_visits}</span> profile visits
            </div>
          )}
          {insight.follows > 0 && (
            <div className="flex items-center gap-2 text-sm text-dun">
              <UserPlus className="w-4 h-4 text-green-400" />
              <span className="text-bone font-medium">{insight.follows}</span> follows
            </div>
          )}
          {insight.saves > 0 && (
            <div className="flex items-center gap-2 text-sm text-dun">
              <Bookmark className="w-4 h-4 text-yellow-400" />
              <span className="text-bone font-medium">{insight.saves}</span> saves
            </div>
          )}
          {insight.shares > 0 && (
            <div className="flex items-center gap-2 text-sm text-dun">
              <Share2 className="w-4 h-4 text-blue-400" />
              <span className="text-bone font-medium">{insight.shares}</span> shares
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function PostDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { data: post, isLoading } = usePost(id as string);
  const { data: metricHistory } = usePostMetrics(id as string);
  const { data: comments } = usePostComments(id as string);
  const [diagnostic, setDiagnostic] = useState<any>(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [remixes, setRemixes] = useState<any[]>([]);
  const [remixLoading, setRemixLoading] = useState(false);
  const [mediaFiles, setMediaFiles] = useState<{ filename: string; size_bytes: number; url: string }[]>([]);
  const [activeMediaIdx, setActiveMediaIdx] = useState(0);
  const [showAllComments, setShowAllComments] = useState(false);

  useEffect(() => {
    if (id) {
      api.getPostMedia(id as string).then(res => {
        if (res?.files?.length) setMediaFiles(res.files);
      }).catch(() => {});
    }
  }, [id]);

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
  const insight = post.latest_insight;

  // Separate top-level comments and replies
  const topComments = comments?.filter((c: any) => !c.parent_comment_id) || [];
  const replies = comments?.filter((c: any) => c.parent_comment_id) || [];
  const repliesByParent = replies.reduce((acc: Record<string, any[]>, r: any) => {
    (acc[r.parent_comment_id] = acc[r.parent_comment_id] || []).push(r);
    return acc;
  }, {} as Record<string, any[]>);

  // Sort by likes
  const sortedComments = [...topComments].sort((a: any, b: any) => b.comment_like_count - a.comment_like_count);
  const displayComments = showAllComments ? sortedComments : sortedComments.slice(0, 10);

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
        <p className="text-bone whitespace-pre-line">{post.caption || 'No caption'}</p>
      </div>

      {/* Media Gallery */}
      {mediaFiles.length > 0 && (
        <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <ImageIcon className="w-4 h-4 text-dun" />
            <h3 className="text-sm font-medium text-dun">
              Media {mediaFiles.length > 1 && `(${activeMediaIdx + 1}/${mediaFiles.length})`}
            </h3>
          </div>
          <div className="relative flex items-center justify-center bg-ebony/40 rounded-lg overflow-hidden" style={{ minHeight: 300 }}>
            {mediaFiles[activeMediaIdx]?.filename.endsWith('.mp4') ? (
              <video
                key={mediaFiles[activeMediaIdx].url}
                src={mediaFiles[activeMediaIdx].url}
                controls
                className="max-h-[500px] w-auto rounded"
              />
            ) : (
              <img
                key={mediaFiles[activeMediaIdx].url}
                src={mediaFiles[activeMediaIdx].url}
                alt={`Post media ${activeMediaIdx + 1}`}
                className="max-h-[500px] w-auto object-contain rounded"
              />
            )}
            {mediaFiles.length > 1 && (
              <>
                <button
                  onClick={() => setActiveMediaIdx(i => (i - 1 + mediaFiles.length) % mediaFiles.length)}
                  className="absolute left-2 top-1/2 -translate-y-1/2 bg-ebony/70 hover:bg-ebony/90 text-bone p-1.5 rounded-full transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setActiveMediaIdx(i => (i + 1) % mediaFiles.length)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-ebony/70 hover:bg-ebony/90 text-bone p-1.5 rounded-full transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </>
            )}
          </div>
          {mediaFiles.length > 1 && (
            <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
              {mediaFiles.map((file, i) => (
                <button
                  key={file.filename}
                  onClick={() => setActiveMediaIdx(i)}
                  className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-colors ${
                    i === activeMediaIdx ? 'border-sage' : 'border-transparent opacity-60 hover:opacity-100'
                  }`}
                >
                  {file.filename.endsWith('.mp4') ? (
                    <div className="w-full h-full bg-ebony/60 flex items-center justify-center">
                      <Play className="w-5 h-5 text-bone" />
                    </div>
                  ) : (
                    <img src={file.url} alt={`Thumb ${i + 1}`} className="w-full h-full object-cover" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

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

      {/* Instagram Insights */}
      {post.latest_insight && <InsightsSection insight={post.latest_insight} />}

      {/* Comments Section */}
      {comments?.length > 0 && (
        <div className="bg-reseda/20 border border-reseda/30 rounded-xl p-6">
          <h3 className="text-lg font-bold flex items-center gap-2 mb-4 text-bone">
            <MessageCircle className="w-5 h-5 text-sage" />
            Comments
            <span className="text-sm font-normal text-dun/60 ml-1">({comments.length})</span>
          </h3>
          <div className="space-y-3">
            {displayComments.map((c: any) => (
              <div key={c.id}>
                <div className="p-3 bg-ebony/40 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-sage">@{c.username}</span>
                    <div className="flex items-center gap-3 text-xs text-dun/50">
                      {c.comment_like_count > 0 && (
                        <span className="flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" /> {c.comment_like_count}
                        </span>
                      )}
                      {c.reply_count > 0 && (
                        <span className="flex items-center gap-1">
                          <Reply className="w-3 h-3" /> {c.reply_count}
                        </span>
                      )}
                      <span>{new Date(c.commented_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <p className="text-sm text-bone/90">{c.text}</p>
                </div>
                {/* Replies */}
                {repliesByParent[c.id]?.map((r: any) => (
                  <div key={r.id} className="ml-6 mt-2 p-3 bg-ebony/30 rounded-lg border-l-2 border-reseda/30">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-sage/80">@{r.username}</span>
                      <div className="flex items-center gap-3 text-xs text-dun/40">
                        {r.comment_like_count > 0 && (
                          <span className="flex items-center gap-1">
                            <ThumbsUp className="w-3 h-3" /> {r.comment_like_count}
                          </span>
                        )}
                        <span>{new Date(r.commented_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <p className="text-sm text-bone/80">{r.text}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {sortedComments.length > 10 && (
            <button
              onClick={() => setShowAllComments(!showAllComments)}
              className="mt-4 text-sm text-sage hover:text-sage/80 transition-colors"
            >
              {showAllComments ? 'Show less' : `Show all ${sortedComments.length} comments`}
            </button>
          )}
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
            {diagnostic.metadata_json?.discovery_analysis && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-dun">Discovery Analysis</h4>
                <div className="p-3 bg-ebony/40 rounded-lg space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-dun text-sm">Discovery Score:</span>
                    <span className={`text-sm font-medium px-2 py-0.5 rounded-full ${
                      diagnostic.metadata_json.discovery_analysis.discovery_score === 'high'
                        ? 'bg-green-900/40 text-green-300'
                        : diagnostic.metadata_json.discovery_analysis.discovery_score === 'medium'
                        ? 'bg-yellow-900/40 text-yellow-300'
                        : 'bg-red-900/40 text-red-300'
                    }`}>
                      {diagnostic.metadata_json.discovery_analysis.discovery_score}
                    </span>
                  </div>
                  {diagnostic.metadata_json.discovery_analysis.top_source && (
                    <p className="text-sm text-bone">
                      <span className="text-dun">Top Source:</span> {diagnostic.metadata_json.discovery_analysis.top_source}
                    </p>
                  )}
                  {diagnostic.metadata_json.discovery_analysis.recommendation && (
                    <p className="text-sm text-sage">{diagnostic.metadata_json.discovery_analysis.recommendation}</p>
                  )}
                </div>
              </div>
            )}
            {diagnostic.metadata_json?.comment_analysis && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-dun">Comment Analysis</h4>
                <div className="p-3 bg-ebony/40 rounded-lg space-y-2">
                  {diagnostic.metadata_json.comment_analysis.sentiment && (
                    <p className="text-sm text-bone">
                      <span className="text-dun">Sentiment:</span> {diagnostic.metadata_json.comment_analysis.sentiment}
                    </p>
                  )}
                  {diagnostic.metadata_json.comment_analysis.themes?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {diagnostic.metadata_json.comment_analysis.themes.map((t: string, i: number) => (
                        <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-sage/20 text-sage">{t}</span>
                      ))}
                    </div>
                  )}
                  {diagnostic.metadata_json.comment_analysis.engagement_quality && (
                    <p className="text-sm text-bone">
                      <span className="text-dun">Quality:</span> {diagnostic.metadata_json.comment_analysis.engagement_quality}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-dun/60 text-sm">Click Generate to get an AI analysis of this post including comment sentiment.</p>
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
