import useSWR from 'swr';
import { api } from './api';

export function useAccounts() {
  return useSWR('accounts', () => api.getAccounts());
}

export function usePosts(accountId: string | null) {
  return useSWR(accountId ? `posts-${accountId}` : null, () => api.getPosts(accountId!));
}

export function usePost(postId: string | null) {
  return useSWR(postId ? `post-${postId}` : null, () => api.getPost(postId!));
}

export function usePostMetrics(postId: string | null) {
  return useSWR(postId ? `metrics-${postId}` : null, () => api.getPostMetrics(postId!));
}

export function useAccountMetrics(accountId: string | null, days = 7) {
  return useSWR(accountId ? `account-metrics-${accountId}-${days}` : null, () => api.getAccountMetrics(accountId!, days));
}

export function useDailyBrief(accountId: string | null) {
  return useSWR(accountId ? `brief-${accountId}` : null, () => api.getTodayBrief(accountId!));
}

export function useRecommendations(accountId: string | null) {
  return useSWR(accountId ? `recs-${accountId}` : null, () => api.getRecommendations(accountId!));
}

export function useBaseline(accountId: string | null) {
  return useSWR(accountId ? `baseline-${accountId}` : null, () => api.getBaseline(accountId!));
}
