import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Code2, Github } from "lucide-react";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CodeMind AI - Chat with GitHub Repositories",
  description: "RAG-based platform for intelligent codebase conversations",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          {/* Header */}
          <header className="border-b border-border bg-card">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <Link href="/" className="flex items-center space-x-3 hover:opacity-80 transition">
                  <div className="bg-primary p-2 rounded-lg">
                    <Code2 className="h-6 w-6 text-primary-foreground" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-foreground">CodeMind AI</h1>
                    <p className="text-xs text-muted-foreground">Chat with your codebase</p>
                  </div>
                </Link>

                <nav className="flex items-center space-x-4">
                  <Link
                    href="/"
                    className="text-sm text-muted-foreground hover:text-foreground transition"
                  >
                    Home
                  </Link>
                  <a
                    href="https://github.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground transition"
                  >
                    <Github className="h-5 w-5" />
                  </a>
                </nav>
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="flex-1">
            {children}
          </main>

          {/* Footer Removed */}
        </div>
      </body>
    </html>
  );
}