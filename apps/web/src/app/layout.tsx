import type { Metadata } from "next";
import { IBM_Plex_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Per the UI brief / Next.js stack guideline: fonts via next/font on <body>,
// never per-page. IBM Plex Sans (UI) + JetBrains Mono (timecodes/numerics).
const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Agent Flight Recorder",
  description:
    "Forensic black-box recorder for agent/app runs — differential divergence replay.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Force dark — no theme toggle (forensic tools don't have a light mode).
  return (
    <html lang="en" className={`dark ${plexSans.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
