"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Layers, Loader2, RotateCw, Sparkles } from "lucide-react";
import type { Flashcard } from "@/lib/types";

interface FlashcardTabProps {
  cards: Flashcard[];
  generating: boolean;
  onGenerate: () => Promise<void>;
  onReview: (cardId: string, level: "again" | "hard" | "good" | "easy") => Promise<void>;
}

const MASTERY_LABELS: Record<string, { label: string; badge: string }> = {
  again: { label: "다시 암기", badge: "bg-rose-100 text-rose-700" },
  hard: { label: "어려움", badge: "bg-amber-100 text-amber-700" },
  good: { label: "알맞음", badge: "bg-teal-100 text-teal-700" },
  easy: { label: "완벽함", badge: "bg-emerald-100 text-emerald-700" },
};

export default function FlashcardTab({
  cards,
  generating,
  onGenerate,
  onReview,
}: FlashcardTabProps) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  const safeIndex = cards.length > 0 ? Math.min(index, cards.length - 1) : 0;
  const current = cards[safeIndex];

  const handleReview = async (level: "again" | "hard" | "good" | "easy") => {
    if (!current) return;
    await onReview(current.id, level);
    setFlipped(false);
    if (safeIndex < cards.length - 1) {
      setIndex(safeIndex + 1);
    }
  };

  if (cards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-16 text-center">
        <Layers className="h-10 w-10 text-teal-600" />
        <h3 className="mt-3 text-base font-bold text-slate-900">AI 플래시카드 (Tikonote Smartcards)</h3>
        <p className="mt-1 max-w-md text-xs text-slate-500">
          핵심 의학용어, 약물 기전, 진단 기준을 앞·뒷면 암기카드로 자동 생성해 간격 반복 학습을 할 수 있습니다.
        </p>
        <button
          type="button"
          disabled={generating}
          onClick={onGenerate}
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-teal-700 disabled:opacity-50"
        >
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>암기카드 생성 중...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              <span>플래시카드 8장 자동 생성</span>
            </>
          )}
        </button>
      </div>
    );
  }

  const masteryInfo = MASTERY_LABELS[current.mastery_level] || MASTERY_LABELS.again;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-700">
            카드 {safeIndex + 1} / {cards.length}
          </span>
          <span className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${masteryInfo.badge}`}>
            {masteryInfo.label}
          </span>
        </div>
        <button
          type="button"
          disabled={generating}
          onClick={onGenerate}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          <span>카드 추가 생성</span>
        </button>
      </div>

      {/* 카드 플립 영역 */}
      <button
        type="button"
        onClick={() => setFlipped((f) => !f)}
        className={`flex min-h-[240px] w-full flex-col items-center justify-center rounded-2xl border p-8 text-center shadow-xs transition ${
          flipped
            ? "border-teal-300 bg-teal-50/70"
            : "border-slate-200 bg-white hover:border-teal-200"
        }`}
      >
        <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-600">
          {flipped ? "뒷면 · 정답 및 기전" : `앞면 · ${current.category_tag}`}
        </span>
        <p className="mt-4 whitespace-pre-line text-base font-bold leading-relaxed text-slate-900">
          {flipped ? current.back_text : current.front_text}
        </p>
        <span className="mt-6 inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
          <RotateCw className="h-3 w-3" />
          <span>클릭하여 {flipped ? "앞면" : "정답"} 보기</span>
        </span>
      </button>

      {/* 숙련도 체크 버튼 */}
      <div className="grid grid-cols-4 gap-2">
        <button
          type="button"
          onClick={() => handleReview("again")}
          className="rounded-xl border border-rose-200 bg-rose-50 py-2.5 text-xs font-bold text-rose-700 hover:bg-rose-100"
        >
          다시 (오늘)
        </button>
        <button
          type="button"
          onClick={() => handleReview("hard")}
          className="rounded-xl border border-amber-200 bg-amber-50 py-2.5 text-xs font-bold text-amber-700 hover:bg-amber-100"
        >
          어려움 (1일)
        </button>
        <button
          type="button"
          onClick={() => handleReview("good")}
          className="rounded-xl border border-teal-200 bg-teal-50 py-2.5 text-xs font-bold text-teal-700 hover:bg-teal-100"
        >
          알맞음 (3일)
        </button>
        <button
          type="button"
          onClick={() => handleReview("easy")}
          className="rounded-xl border border-emerald-200 bg-emerald-50 py-2.5 text-xs font-bold text-emerald-700 hover:bg-emerald-100"
        >
          쉬움 (7일)
        </button>
      </div>

      {/* 좌우 탐색 */}
      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          disabled={safeIndex <= 0}
          onClick={() => {
            setIndex(safeIndex - 1);
            setFlipped(false);
          }}
          className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
          <span>이전 카드</span>
        </button>
        <button
          type="button"
          disabled={safeIndex >= cards.length - 1}
          onClick={() => {
            setIndex(safeIndex + 1);
            setFlipped(false);
          }}
          className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-30"
        >
          <span>다음 카드</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

