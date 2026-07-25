import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PriorLock",
  description:
    "A Harbor-native benchmark measuring prior-override capability in AI agents.",
  openGraph: {
    title: "PriorLock",
    description:
      "A Harbor-native benchmark measuring prior-override capability in AI agents.",
    type: "website",
    url: "https://phoenixlibbi.github.io/PriorLock-RL-env",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="antialiased font-sans" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
