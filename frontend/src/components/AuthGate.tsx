"use client";

import { useEffect, useState } from "react";
import { Loader2, Lock, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [passcode, setPasscode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const checkStatus = async () => {
    setChecking(true);
    try {
      const status = await api.getAuthStatus();
      setAuthenticated(!status.auth_required || status.authenticated);
    } catch {
      // 서버 일시 슬립/오류 시에도 인증 상태를 안전하게 잠금으로 두거나 재시도 가능
      setAuthenticated(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const handleExpired = () => setAuthenticated(false);
    window.addEventListener("medstudy:auth-expired", handleExpired);
    return () => window.removeEventListener("medstudy:auth-expired", handleExpired);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await api.login(passcode);
      setPasscode("");
      setAuthenticated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "패스코드 확인에 실패했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  if (checking) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
        <p className="text-xs font-medium text-slate-500">포털 인증 상태를 확인하는 중...</p>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="flex items-center gap-2.5">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-white">
              <Stethoscope className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-base font-bold text-slate-900">MedStudy Portal</h1>
              <p className="text-xs text-slate-500">의대생 전용 학습 포털</p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <div>
              <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <Lock className="h-3.5 w-3.5 text-teal-600" />
                <span>접근 패스코드</span>
              </label>
              <input
                type="password"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value)}
                placeholder="패스코드를 입력하세요"
                autoFocus
                className="mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm focus:border-teal-500 focus:outline-none"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting || !passcode.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 py-2.5 text-sm font-bold text-white hover:bg-teal-700 disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <span>잠금 해제</span>}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

