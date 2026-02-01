import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Winu Bot - AI Market Intelligence Chat',
  description: 'AI-powered cryptocurrency market analysis using Llama 3.1. Get real-time insights from Binance, CoinMarketCap, and historical trading data.',
  keywords: 'cryptocurrency, trading, market analysis, AI, Llama, Binance, CoinMarketCap',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

