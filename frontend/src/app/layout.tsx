import type { Metadata } from "next";
import "./globals.css";
import AuthGate from "@/components/AuthGate";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "MedStudy Portal | 의대생 AI 학습 포털",
  description: "수업자료 요약, 의학용어 해설, 근거 링크, 마인드맵, 예상문제 및 파인만 튜터",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <AuthGate>
          <Navbar />
          <main>{children}</main>
        </AuthGate>
      </body>
    </html>
  );
}
