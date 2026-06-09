import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import AppLayout from "@/components/layout/AppLayout";
import { Providers } from "@/lib/providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "AI Multi-Agent Enterprise Workspace",
  description: "Enterprise AI Knowledge Work Platform with Multi-Agent Collaboration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Providers><AppLayout>{children}</AppLayout></Providers>
      </body>
    </html>
  );
}
