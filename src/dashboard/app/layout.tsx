import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { WebSocketProvider } from '@/components/websocket-provider';
import { MessageSquare, Sparkles } from 'lucide-react';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'Facto Dashboard - Telegram Message Logs',
  description: 'View, search, and manage your Telegram group message logs with real-time updates',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <WebSocketProvider>
          <div className="min-h-screen bg-background">
            {/* Modern Header with Glass Effect */}
            <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
              <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex h-16 items-center justify-between">
                  {/* Logo & Brand */}
                  <a
                    href="/"
                    className="flex items-center gap-3 transition-transform hover:scale-[1.02]"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-primary shadow-lg shadow-primary/20">
                      <MessageSquare className="h-5 w-5 text-primary-foreground" />
                    </div>
                    <div className="hidden sm:block">
                      <h1 className="text-xl font-bold tracking-tight text-gradient">
                        Facto Dashboard
                      </h1>
                      <p className="text-xs text-muted-foreground">
                        Message Analytics
                      </p>
                    </div>
                  </a>

                  {/* Right side - Badge/Status */}
                  <div className="flex items-center gap-3">
                    <div className="hidden sm:flex items-center gap-2 rounded-full bg-accent/10 px-4 py-1.5 text-sm font-medium text-accent-foreground">
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Live Updates</span>
                    </div>
                  </div>
                </div>
              </div>
            </header>

            {/* Main Content */}
            <main className="container mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 sm:py-8">
              <div className="animate-fade-in">
                {children}
              </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-border/40 bg-muted/30 py-6 mt-12">
              <div className="container mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
                  <p>
                    © 2026 Facto Dashboard. Built with Next.js & MongoDB.
                  </p>
                  <p className="flex items-center gap-1">
                    Powered by{" "}
                    <span className="font-semibold text-primary">
                      Real-time Analytics
                    </span>
                  </p>
                </div>
              </div>
            </footer>
          </div>
        </WebSocketProvider>
      </body>
    </html>
  );
}
