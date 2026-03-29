'use client';
import { useState, useEffect } from 'react';
import { useAccounts, usePosts } from '@/lib/hooks';
import { api } from '@/lib/api';
import { Eye, Heart, MessageCircle, Play, Image as ImageIcon, Layers, Film } from 'lucide-react';
import Link from 'next/link';

function PostCard({ post }: { post: any }) {
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  const m = post.latest_metrics;

  useEffect(() => {
    api.getPostMedia(post.id).then(res => {
      const img = res?.files?.find((f: any) => !f.filename.endsWith('.mp4'));
      if (img) setThumbUrl(img.url);
      else if (res?.files?.length) setThumbUrl(res.files[0].url);
    }).catch(() => {});
  }, [post.id]);

  const TypeIcon = post.post_type === 'reel' || post.post_type === 'video'
    ? Film
    : post.post_type === 'carousel'
    ? Layers
    : ImageIcon;

  return (
    <Link href={`/dashboard/posts/${post.id}`} className="relative aspect-square overflow-hidden bg-ebony/40 group rounded-lg">
      {thumbUrl ? (
        <img src={thumbUrl} alt="" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <TypeIcon className="w-8 h-8 text-dun/30" />
        </div>
      )}

      {/* Type badge */}
      <div className="absolute top-2 right-2">
        <TypeIcon className="w-4 h-4 text-white drop-shadow-lg" />
      </div>

      {/* Hover overlay with metrics */}
      <div className="absolute inset-0 bg-ebony/75 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center">
        <div className="flex items-center gap-5 text-bone text-sm font-medium">
          {m?.likes != null && (
            <span className="flex items-center gap-1.5">
              <Heart className="w-4 h-4 fill-current" />
              {formatNum(m.likes)}
            </span>
          )}
          {m?.views != null && m.views > 0 && (
            <span className="flex items-center gap-1.5">
              <Eye className="w-4 h-4" />
              {formatNum(m.views)}
            </span>
          )}
          {m?.comments != null && (
            <span className="flex items-center gap-1.5">
              <MessageCircle className="w-4 h-4" />
              {formatNum(m.comments)}
            </span>
          )}
        </div>
      </div>

      {/* Video play indicator */}
      {(post.post_type === 'reel' || post.post_type === 'video') && (
        <div className="absolute bottom-2 left-2">
          <Play className="w-4 h-4 text-white fill-white drop-shadow-lg" />
        </div>
      )}
    </Link>
  );
}

function formatNum(n: number): string {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

export default function PostsPage() {
  const { data: accounts } = useAccounts();
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    if (accounts?.length && !selectedAccount) {
      setSelectedAccount(accounts[0].id);
    }
  }, [accounts, selectedAccount]);

  const { data: posts, isLoading } = usePosts(selectedAccount);

  const filteredPosts = posts?.filter((p: any) =>
    filterType === 'all' || p.post_type === filterType
  );

  const typeCounts = posts?.reduce((acc: Record<string, number>, p: any) => {
    acc[p.post_type] = (acc[p.post_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-bone">Posts</h1>
        <div className="flex items-center gap-3">
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
      </div>

      {/* Type filters */}
      {posts?.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setFilterType('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filterType === 'all' ? 'bg-sage/30 text-bone' : 'bg-reseda/20 text-dun hover:text-bone'
            }`}
          >
            All ({posts.length})
          </button>
          {Object.entries(typeCounts).map(([type, count]) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterType === type ? 'bg-sage/30 text-bone' : 'bg-reseda/20 text-dun hover:text-bone'
              }`}
            >
              {type} ({count as number})
            </button>
          ))}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-3 gap-1 md:gap-2">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="aspect-square bg-reseda/20 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : !filteredPosts?.length ? (
        <div className="text-center py-20 text-dun/60">
          <p>No posts found. Import data via CSV or connect a platform.</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-1 md:gap-2">
          {filteredPosts.map((post: any) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
