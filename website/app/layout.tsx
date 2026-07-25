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
  title: "PriorLock — Domain-Agnostic RL Environment for Prior Override",
  description:
    "PriorLock: A Domain-Agnostic Reinforcement Learning Environment for Measuring and Training Prior Override in Autonomous Agents. Created by Muhammad Labeeb Tariq.",
  authors: [{ name: "Muhammad Labeeb Tariq", url: "https://github.com/phoenixlibbi" }],
  creator: "Muhammad Labeeb Tariq",
  openGraph: {
    title: "PriorLock: Domain-Agnostic RL Environment for Prior Override",
    description:
      "A domain-agnostic reinforcement learning environment for measuring and training prior override in autonomous agents. Created by Muhammad Labeeb Tariq.",
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
    <html lang="en" className={`${sans.variable} ${mono.variable}`} suppressHydrationWarning>
      <body className="antialiased font-sans" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
