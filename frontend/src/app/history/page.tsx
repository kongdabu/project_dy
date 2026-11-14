"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Brain,
  CheckCircle2,
  ExternalLink,
  History as HistoryIcon,
  Layers,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { HistoryResponse } from "@/lib/types";

export default function HistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [revealedWrongIds, setRevealedWrongIds] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api
      .getHistory()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center text-sm text-slate-500">
        이력 데이터를 불러오지 못했습니다. 백엔드 서버 상태를 확인해 주세요.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8">
      <div>
        <h1 className="text-xl font-bold text-slate-900">통합 학습 이력 &amp; 오답노트</h1>
        <p className="mt-1 text-sm text-slate-500">
          문제 풀이 점수, 틀린 문제 복습, 다시 암기할 플래시카드, 파인만 진단 기록을 한곳에서 관리합니다.
        </p>
      </div>

      {/* 요약 지표 */}
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
            <BookOpen className="h-4 w-4 text-teal-600" />
            <span>등록된 학습 자료</span>
          </div>
          <p className="mt-2 text-2xl font-extrabold text-slate-900">{data.documents_count}개</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
            <HistoryIcon className="h-4 w-4 text-blue-600" />
            <span>예상문제 풀이 횟수</span>
          </div>
          <p className="mt-2 text-2xl font-extrabold text-slate-900">{data.attempts.length}회</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
            <AlertCircle className="h-4 w-4 text-rose-600" />
            <span>오답노트 문항</span>
          </div>
          <p className="mt-2 text-2xl font-extrabold text-rose-600">{data.wrong_questions.length}문항</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
            <Layers className="h-4 w-4 text-amber-600" />
            <span>복습 필요 암기카드</span>
          </div>
          <p className="mt-2 text-2xl font-extrabold text-amber-600">
            {data.review_flashcards.length}장
          </p>
        </div>
      </div>

      {/* 오답노트 섹션 */}
      <section className="space-y-3">
        <h2 className="text-base font-bold text-slate-900">오답노트 (틀린 문제 다시 보기)</h2>
        {data.wrong_questions.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
            <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500" />
            <p className="mt-2 font-semibold text-slate-700">현재 오답 문항이 없습니다!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {data.wrong_questions.map((wq) => {
              const revealed = Boolean(revealedWrongIds[wq.id]);
              return (
                <div key={wq.id} className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700">
                        {wq.question_type === "MCQ" ? "4지선다 오답" : "서술형 오답"}
                      </span>
                      <span className="text-xs font-semibold text-slate-500">{wq.document_title}</span>
                    </div>
                    <Link
                      href={`/study/${wq.document_id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-teal-700 hover:underline"
                    >
                      <span>자료로 이동</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>

                  <p className="mt-3 text-sm font-semibold text-slate-900">{wq.question_text}</p>

                  {wq.question_type === "MCQ" && wq.options?.length > 0 && (
                    <ul className="mt-3 space-y-1 text-xs text-slate-600">
                      {wq.options.map((opt, idx) => (
                        <li key={idx}>
                          {idx + 1}. {opt}
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
                    <span className="text-xs text-rose-600">
                      내 답안: <span className="font-bold">{wq.last_user_answer || "(미작성)"}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        setRevealedWrongIds((prev) => ({ ...prev, [wq.id]: !prev[wq.id] }))
                      }
                      className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                    >
                      {revealed ? "정답/해설 숨기기" : "정답 및 해설 확인"}
                    </button>
                  </div>

                  {revealed && (
                    <div className="mt-3 rounded-xl bg-slate-50 p-4 text-xs space-y-1.5">
                      <p className="font-bold text-emerald-700">정답: {wq.correct_answer}</p>
                      <p className="leading-relaxed text-slate-700">{wq.explanation}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 최근 문제 풀이 이력 */}
      <section className="space-y-3">
        <h2 className="text-base font-bold text-slate-900">최근 문제 풀이 이력</h2>
        {data.attempts.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center text-xs text-slate-500">
            아직 문제 풀이 기록이 없습니다.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-semibold">자료명</th>
                  <th className="px-4 py-3 font-semibold">문제 세트</th>
                  <th className="px-4 py-3 font-semibold">난이도</th>
                  <th className="px-4 py-3 font-semibold">점수</th>
                  <th className="px-4 py-3 font-semibold">풀이 일시</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.attempts.map((att) => (
                  <tr key={att.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      <Link href={`/study/${att.document_id}`} className="hover:text-teal-700">
                        {att.document_title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{att.quiz_title}</td>
                    <td className="px-4 py-3 text-slate-500">{att.difficulty}</td>
                    <td className="px-4 py-3 font-bold text-teal-700">
                      {att.score} / {att.total_questions}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(att.attempted_at).toLocaleString("ko-KR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 파인만 튜터 최근 기록 */}
      {data.feynman_sessions.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
            <Brain className="h-4 w-4 text-teal-600" />
            <span>최근 파인만 &amp; 블러팅 평가</span>
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.feynman_sessions.map((fs) => (
              <Link
                key={fs.id}
                href={`/study/${fs.document_id}`}
                className="rounded-2xl border border-slate-200 bg-white p-4 hover:border-teal-300"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-900">{fs.topic}</span>
                  <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-700">
                    {fs.ai_feedback.understanding_score}점
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-xs text-slate-600">{fs.ai_feedback.coach_summary}</p>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

