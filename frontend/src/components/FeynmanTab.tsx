"use client";

import { useState } from "react";
import { Brain, CheckCircle2, ExternalLink, Loader2, AlertTriangle, Sparkles } from "lucide-react";
import type { FeynmanSession } from "@/lib/types";

interface FeynmanTabProps {
  docTitle: string;
  sessions: FeynmanSession[];
  evaluating: boolean;
  onEvaluate: (topic: string, userExplanation: string) => Promise<void>;
  onJumpToPage: (page: number) => void;
}

export default function FeynmanTab({
  docTitle,
  sessions,
  evaluating,
  onEvaluate,
  onJumpToPage,
}: FeynmanTabProps) {
  const [topic, setTopic] = useState(docTitle);
  const [explanation, setExplanation] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!explanation.trim()) return;
    await onEvaluate(topic.trim() || docTitle, explanation);
    setExplanation("");
  };

  return (
    <div className="space-y-6">
      {/* 블러팅 입력 폼 */}
      <form
        onSubmit={handleSubmit}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs space-y-4"
      >
        <div className="flex items-start gap-2.5">
          <Brain className="mt-0.5 h-5 w-5 shrink-0 text-teal-600" />
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              파인만 &amp; 블러팅(Blurting) AI 튜터
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              자료를 보지 않고 머릿속에 기억나는 핵심 기전·임상 양상·치료를 동료에게 설명하듯 적어보세요. AI가 원본과 대조해 빈틈을 짚어줍니다.
            </p>
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600">설명할 주제</label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="예: 심부전의 병태생리 및 약물 치료 기전"
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-xs focus:border-teal-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-600">
            백지 인출 서술 (블러팅)
          </label>
          <textarea
            rows={5}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="기억나는 대로 자유롭게 설명해 보세요..."
            className="mt-1 w-full rounded-xl border border-slate-200 p-3 text-xs leading-relaxed focus:border-teal-500 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={evaluating || !explanation.trim()}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 py-2.5 text-xs font-bold text-white hover:bg-teal-700 disabled:opacity-50"
        >
          {evaluating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI 튜터가 이해도를 진단하는 중...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>제출하고 빈틈 진단받기</span>
            </>
          )}
        </button>
      </form>

      {/* 평가 결과 목록 */}
      {sessions.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-700">진단 리포트 기록</h4>
          {sessions.map((s) => {
            const fb = s.ai_feedback;
            return (
              <div key={s.id} className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-bold text-slate-900">{s.topic}</span>
                  <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-extrabold text-teal-700">
                    이해도 {fb.understanding_score}점
                  </span>
                </div>

                <p className="rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
                  <span className="font-semibold text-slate-800">내 서술: </span>
                  {s.user_explanation}
                </p>

                <div className="grid gap-3 sm:grid-cols-2 text-xs">
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
                    <p className="flex items-center gap-1 font-bold text-emerald-800">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>잘 이해한 핵심</span>
                    </p>
                    <ul className="mt-1.5 list-disc pl-4 space-y-1 text-emerald-900">
                      {fb.strengths.map((st, idx) => (
                        <li key={idx}>{st}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
                    <p className="flex items-center gap-1 font-bold text-amber-800">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>누락된 핵심 개념</span>
                    </p>
                    <ul className="mt-1.5 list-disc pl-4 space-y-1 text-amber-900">
                      {fb.missing_concepts.map((mc, idx) => (
                        <li key={idx}>{mc}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                {fb.misconceptions && fb.misconceptions.length > 0 && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900">
                    <span className="font-bold">교정이 필요한 오개념: </span>
                    {fb.misconceptions.join(" / ")}
                  </div>
                )}

                <div className="flex items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs">
                  <p className="text-slate-700">
                    <span className="font-bold text-slate-900">튜터 총평: </span>
                    {fb.coach_summary}
                  </p>
                  <button
                    type="button"
                    onClick={() => onJumpToPage(fb.reference_page || 1)}
                    className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-teal-700 hover:bg-teal-50"
                  >
                    <ExternalLink className="h-3 w-3" />
                    <span>p.{fb.reference_page || 1} 복습</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

