"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BookOpen, History, Lock, Stethoscope, Upload } from "lucide-react";
import { clearAuthToken, getAuthToken } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(Boolean(getAuthToken()));
  }, [pathname]);

  const navItems = [
    { href: "/", label: "대시보드", icon: BookOpen },
    { href: "/upload", label: "자료 업로드", icon: Upload },
    { href: "/history", label: "이력 / 오답노트", icon: History },
  ];

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 font-bold text-slate-900">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-white">
              <Stethoscope className="h-4 w-4" />
            </span>
            <span className="text-base tracking-tight">MedStudy Portal</span>
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-teal-50 text-teal-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {hasToken && (
          <button
            type="button"
            onClick={() => clearAuthToken()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100"
          >
            <Lock className="h-3.5 w-3.5" />
            <span>포털 잠금</span>
          </button>
        )}
      </div>
    </header>
  );
}
