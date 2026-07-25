import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
