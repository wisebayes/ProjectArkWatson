import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ArkWatson - Disaster Ops Center",
  description: "Live monitoring, classification, and response planning",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen bg-[#0b111e]`}>
        <div className="fixed inset-0 -z-10 hero opacity-20" />
        <div className="mx-auto max-w-[1400px] px-4 py-6">{children}</div>
      </body>
    </html>
  );
}
