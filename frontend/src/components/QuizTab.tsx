"use client";

import { useState } from "react";
import { CheckCircle2, ExternalLink, HelpCircle, Loader2, PlusCircle, XCircle } from "lucide-react";
import type { QuizSet, QuizSubmitResponse, QuizSubmitResultItem } from "@/lib/types";

interface QuizTabProps {
  quizzes: QuizSet[];
  generating: boolean;
  submitting: boolean;
  onGenerateQuiz: (mcqCount: number, essayCount: number, difficulty: string) => Promise<void>;
  onSubmitQuiz: (
    quizId: string,
    answers: Array<{ question_id: string; answer: string }>
  ) => Promise<QuizSubmitResponse>;
  onJumpToPage: (page: number, quote?: string) => void;
}

export default function QuizTab({
  quizzes,
  generating,
  submitting,
  onGenerateQuiz,
  onSubmitQuiz,
  onJumpToPage,
}: QuizTabProps) {
  const [mcqCount, setMcqCount] = useState(3);
  const [essayCount, setEssayCount] = useState(2);
  const [difficulty, setDifficulty] = useState("임상응용");

  const [selectedQuizId, setSelectedQuizId] = useState<string>("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitResult, setSubmitResult] = useState<QuizSubmitResponse | null>(null);

  const activeQuiz =
    quizzes.find((q) => q.id === selectedQuizId) || quizzes[0] || null;

  const resultMap: Record<string, QuizSubmitResultItem> = {};
  if (submitResult) {
    for (const r of submitResult.results) {
      resultMap[r.question_id] = r;
    }
  }

  const handleGenerate = async () => {
    setSubmitResult(null);
    setAnswers({});
    await onGenerateQuiz(mcqCount, essayCount, difficulty);
    setSelectedQuizId("");
  };

  const handleSubmit = async () => {
    if (!activeQuiz) return;
    const payload = activeQuiz.questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] || "",
    }));
    const res = await onSubmitQuiz(activeQuiz.id, payload);
    setSubmitResult(res);
  };

  return (
    <div className="space-y-6">
      {/* 출제 컨트롤 패널 */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-500">4지선다</label>
              <select
                value={mcqCount}
                onChange={(e) => setMcqCount(Number(e.target.value))}
                className="mt-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold"
              >
                {[0, 1, 2, 3, 5, 8].map((n) => (
                  <option key={n} value={n}>
                    {n}문항
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-500">서술형</label>
              <select
                value={essayCount}
                onChange={(e) => setEssayCount(Number(e.target.value))}
                className="mt-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold"
              >
                {[0, 1, 2, 3, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}문항
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-500">난이도</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="mt-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold"
              >
                <option value="기초개념">기초개념</option>
                <option value="임상응용">임상응용</option>
                <option value="국가고시실전">국가고시실전</option>
              </select>
            </div>
          </div>

          <button
            type="button"
            disabled={generating || mcqCount + essayCount === 0}
            onClick={handleGenerate}
            className="inline-flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-bold text-white hover:bg-teal-700 disabled:opacity-50"
          >
            {generating ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>문제 출제 중...</span>
              </>
            ) : (
              <>
                <PlusCircle className="h-3.5 w-3.5" />
                <span>새 예상문제 출제</span>
              </>
            )}
          </button>
        </div>

        {/* 기존 세트 선택 */}
        {quizzes.length > 1 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3">
            <span className="text-[11px] font-semibold text-slate-500">문제 세트:</span>
            {quizzes.map((qz) => (
              <button
                key={qz.id}
                type="button"
                onClick={() => {
                  setSelectedQuizId(qz.id);
                  setAnswers({});
                  setSubmitResult(null);
                }}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition ${
                  activeQuiz?.id === qz.id
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {qz.title}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 문제 풀이 영역 */}
      {!activeQuiz ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-6 py-14 text-center">
          <HelpCircle className="h-10 w-10 text-teal-600" />
          <p className="mt-3 text-sm font-bold text-slate-900">아직 출제된 예상문제가 없습니다</p>
          <p className="mt-1 text-xs text-slate-500">
            위에서 4지선다와 서술형 문항 수를 고른 뒤 &ldquo;새 예상문제 출제&rdquo;를 눌러보세요.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* 점수 요약 배너 */}
          {submitResult && (
            <div className="flex items-center justify-between rounded-2xl border border-teal-200 bg-teal-50 p-4">
              <div>
                <p className="text-xs font-bold text-teal-800">채점 완료 및 이력 저장됨</p>
                <p className="mt-0.5 text-lg font-extrabold text-teal-950">
                  {submitResult.score} / {submitResult.total_questions} 문항 정답
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSubmitResult(null);
                  setAnswers({});
                }}
                className="rounded-xl bg-white px-3.5 py-2 text-xs font-bold text-teal-700 ring-1 ring-teal-200 hover:bg-teal-100"
              >
                다시 풀기
              </button>
            </div>
          )}

          {activeQuiz.questions.map((q, idx) => {
            const res = resultMap[q.id];
            const userChoice = answers[q.id] || "";

            return (
              <div key={q.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-2xs">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`rounded-md px-2 py-0.5 text-[11px] font-bold ${
                      q.question_type === "MCQ"
                        ? "bg-blue-50 text-blue-700"
                        : "bg-purple-50 text-purple-700"
                    }`}
                  >
                    {q.question_type === "MCQ" ? "4지선다" : "서술형"} · Q{idx + 1}
                  </span>

                  {res && (
                    <span
                      className={`inline-flex items-center gap-1 text-xs font-bold ${
                        res.is_correct ? "text-emerald-600" : "text-rose-600"
                      }`}
                    >
                      {res.is_correct ? (
                        <>
                          <CheckCircle2 className="h-4 w-4" />
                          <span>정답 {res.score_percent !== undefined ? `(${res.score_percent}점)` : ""}</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4" />
                          <span>오답 {res.score_percent !== undefined ? `(${res.score_percent}점)` : ""}</span>
                        </>
                      )}
                    </span>
                  )}
                </div>

                <p className="mt-3 whitespace-pre-line text-sm font-semibold leading-relaxed text-slate-900">
                  {q.question_text}
                </p>

                {/* 4지선다 보기 */}
                {q.question_type === "MCQ" ? (
                  <div className="mt-4 space-y-2">
                    {q.options.map((opt, oIdx) => {
                      const choiceNum = String(oIdx + 1);
                      const isSelected = userChoice === choiceNum;
                      const isAnswer = res && String(res.correct_answer) === choiceNum;
                      const isWrongSelected = res && isSelected && !res.is_correct;

                      let btnStyle = "border-slate-200 bg-white hover:bg-slate-50 text-slate-800";
                      if (res) {
                        if (isAnswer) {
                          btnStyle = "border-emerald-500 bg-emerald-50 text-emerald-900 font-semibold";
                        } else if (isWrongSelected) {
                          btnStyle = "border-rose-400 bg-rose-50 text-rose-900";
                        } else {
                          btnStyle = "border-slate-200 bg-slate-50/50 text-slate-500";
                        }
                      } else if (isSelected) {
                        btnStyle = "border-teal-600 bg-teal-50 text-teal-900 font-semibold";
                      }

                      return (
                        <button
                          key={choiceNum}
                          type="button"
                          disabled={Boolean(res)}
                          onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: choiceNum }))}
                          className={`flex w-full items-start gap-2.5 rounded-xl border p-3 text-left text-xs transition ${btnStyle}`}
                        >
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-[11px] font-bold">
                            {choiceNum}
                          </span>
                          <span className="leading-relaxed">{opt}</span>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="mt-4">
                    <textarea
                      rows={4}
                      disabled={Boolean(res)}
                      value={userChoice}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                      placeholder="핵심 기전과 의학 키워드를 포함하여 서술형 답안을 작성하세요..."
                      className="w-full rounded-xl border border-slate-200 p-3 text-xs leading-relaxed focus:border-teal-500 focus:outline-none disabled:bg-slate-50"
                    />
                  </div>
                )}

                {/* 제출 후 해설 및 근거 표시 */}
                {res && (
                  <div className="mt-4 space-y-2.5 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs">
                    {q.question_type === "ESSAY" && (
                      <>
                        <div>
                          <span className="font-bold text-slate-900">모범 답안: </span>
                          <span className="text-slate-700">{res.correct_answer}</span>
                        </div>
                        {res.ai_feedback && (
                          <div className="rounded-lg bg-purple-50 p-2.5 text-purple-900">
                            <span className="font-bold">AI 채점 피드백: </span>
                            <span>{res.ai_feedback}</span>
                          </div>
                        )}
                        {(res.matched_keywords?.length || res.missing_keywords?.length) ? (
                          <div className="flex flex-wrap gap-1.5">
                            {res.matched_keywords?.map((kw) => (
                              <span key={kw} className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                                ✓ {kw}
                              </span>
                            ))}
                            {res.missing_keywords?.map((kw) => (
                              <span key={kw} className="rounded bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-800">
                                누락: {kw}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </>
                    )}

                    <div>
                      <span className="font-bold text-slate-900">상세 해설: </span>
                      <p className="mt-1 whitespace-pre-line leading-relaxed text-slate-700">
                        {res.explanation}
                      </p>
                    </div>

                    {res.source_reference?.page && (
                      <button
                        type="button"
                        onClick={() =>
                          onJumpToPage(res.source_reference.page, res.source_reference.quote)
                        }
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-teal-700 hover:bg-teal-50"
                      >
                        <ExternalLink className="h-3 w-3" />
                        <span>근거 자료 p.{res.source_reference.page} 확인하기</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {!submitResult && (
            <button
              type="button"
              disabled={submitting}
              onClick={handleSubmit}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 py-3 text-sm font-bold text-white shadow-xs hover:bg-slate-800 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>채점 및 해설 생성 중...</span>
                </>
              ) : (
                <span>답안 제출하고 정답·해설 확인하기</span>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

