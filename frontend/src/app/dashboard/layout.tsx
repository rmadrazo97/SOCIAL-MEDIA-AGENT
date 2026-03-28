'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import DashboardLayout from '@/components/layout/DashboardLayout';
import { CopilotKit } from '@copilotkit/react-core';
import { CopilotPopup } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  useEffect(() => {
    if (!api.isAuthenticated()) {
      router.replace('/login');
    }
  }, [router]);

  const runtimeUrl = '/copilotkit';

  return (
    <CopilotKit runtimeUrl={runtimeUrl}>
      <DashboardLayout>{children}</DashboardLayout>
      <CopilotPopup
        labels={{
          title: "Co-Pilot",
          initial: "Hey! I'm your Social Media Co-Pilot. Ask me anything about your accounts, content performance, or let me help you plan your next post.",
          placeholder: "Ask about your content, metrics, or get ideas...",
        }}
        className="copilot-popup-custom"
      />
    </CopilotKit>
  );
}
