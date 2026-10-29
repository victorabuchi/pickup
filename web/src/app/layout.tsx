import type { Metadata } from 'next';
import { Bricolage_Grotesque, Figtree } from 'next/font/google';
import './globals.css';

const ui = Figtree({ subsets: ['latin'], weight: ['400', '500', '600', '700', '800'], variable: '--font-ui' });
const display = Bricolage_Grotesque({ subsets: ['latin'], weight: ['600', '700', '800'], variable: '--font-display' });

export const metadata: Metadata = {
  title: 'Pickup — pick up where you left off',
  description:
    'Every project on your machine in one place: what state it is in, what you left uncommitted, and what you were actually trying to do.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${ui.variable} ${display.variable}`}>
      <body>{children}</body>
    </html>
  );
}
