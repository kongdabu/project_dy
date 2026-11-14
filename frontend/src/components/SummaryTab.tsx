"use client";

import { BookMarked, ExternalLink, Lightbulb, Loader2, Sparkles, Stethoscope } from "lucide-react";
import type { SummaryRecord } from "@/lib/types";

interface SummaryTabProps {
  summary: SummaryRecord | null;
  loading: boolean;
  onGenerate: () => void;
  onJumpToPage: (page: number, quote?: string) => void;
}

export default function SummaryTab({
  summary,
  loading,
  onGenerate,
  onJumpToPage,
}: SummaryTabProps) {
  if (!summary) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-16 text-center">
        <Sparkles className="h-10 w-10 text-teal-600" />
        <h3 className="mt-3 text-base font-bold text-slate-900">AI 핵심 요약 &amp; 의학용어 해설 생성</h3>
        <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-500">
          Gemini AI가 자료를 분석하여 병태생리·임상양상·치료 핵심 요약, 쉬운 의학용어 사전, 원본 근거 링크, 마인드맵을 한 번에 생성합니다.
        </p>
        <button
          type="button"
          disabled={loading}
          onClick={onGenerate}
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-bold text-white shadow-xs hover:bg-teal-700 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>AI 분석 중 (10~20초 소요)...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>요약 · 용어 · 마인드맵 생성하기</span>
            </>
          )}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 상단 재생성 버튼 & 개요 */}
      <div className="rounded-2xl border border-teal-100 bg-teal-50/60 p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs font-bold text-teal-800">
            <BookMarked className="h-4 w-4" />
            <span>전체 핵심 개요</span>
          </span>
          <button
            type="button"
            disabled={loading}
            onClick={onGenerate}
            className="inline-flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-[11px] font-semibold text-teal-700 ring-1 ring-teal-200 hover:bg-teal-50 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
            <span>다시 분석</span>
          </button>
        </div>
        <p className="mt-2.5 text-sm leading-relaxed text-slate-800">{summary.overview}</p>
      </div>

      {/* 핵심 요약 섹션 */}
      <section className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900">핵심 요약 및 근거 자료</h3>
        {summary.key_points.map((kp, idx) => (
          <div key={idx} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
            <h4 className="text-sm font-bold text-slate-900">
              {idx + 1}. {kp.section}
            </h4>
            <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">
              {kp.summary}
            </p>

            {kp.clinical_pearl && (
              <div className="mt-3 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">
                <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <div>
                  <span className="font-bold">High-Yield Point: </span>
                  <span>{kp.clinical_pearl}</span>
                </div>
              </div>
            )}

            {kp.references && kp.references.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {kp.references.map((ref, rIdx) => (
                  <button
                    key={rIdx}
                    type="button"
                    data-keep-viewer="true"
                    onClick={() => onJumpToPage(ref.page, ref.quote)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-left text-[11px] font-medium text-slate-700 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-800"
                  >
                    <ExternalLink className="h-3 w-3 shrink-0 text-teal-600" />
                    <span className="font-bold">p.{ref.page}</span>
                    <span className="max-w-[220px] truncate text-slate-500">
                      &ldquo;{ref.quote}&rdquo;
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </section>

      {/* 의학용어 쉬운 해설 */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <Stethoscope className="h-4 w-4 text-teal-600" />
          <h3 className="text-sm font-bold text-slate-900">의학용어 쉬운 해설</h3>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {summary.medical_terms.map((item, idx) => (
            <div key={idx} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-2">
                <h4 className="text-sm font-bold text-teal-800">{item.term}</h4>
                <button
                  type="button"
                  data-keep-viewer="true"
                  onClick={() => onJumpToPage(item.page || 1)}
                  className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-teal-50 hover:text-teal-700"
                >
                  p.{item.page || 1}
                </button>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-700">
                <span className="font-semibold text-slate-900">쉬운 풀이: </span>
                {item.simple_explanation}
              </p>
              {item.mechanism && (
                <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
                  <span className="font-semibold text-slate-700">기전/의미: </span>
                  {item.mechanism}
                </p>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

