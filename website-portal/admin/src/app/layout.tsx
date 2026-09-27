import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "مدیریت درس‌گفتارها",
  description: "ویرایش محتوای پورتال",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fa" dir="rtl">
      <body className="min-h-screen bg-bg text-ink antialiased">{children}</body>
    </html>
  );
}
