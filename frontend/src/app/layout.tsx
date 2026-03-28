import type { Metadata } from 'next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Social Media Command Center',
  description: 'AI-powered social media analytics and insights',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ebony text-bone antialiased">
        {children}
      </body>
    </html>
  );
}
