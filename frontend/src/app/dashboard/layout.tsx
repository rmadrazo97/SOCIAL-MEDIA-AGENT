'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/DashboardLayout';

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.replace('/login');
    }
  }, [router]);
  return <DashboardLayout>{children}</DashboardLayout>;
}
