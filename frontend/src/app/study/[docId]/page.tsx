"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  Brain,
  HelpCircle,
  Layers,
  Loader2,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  FeynmanSession,
  Flashcard,
  QuizSet,
  StudyDocument,
  SummaryRecord,
} from "@/lib/types";
import DocumentViewer from "@/components/DocumentViewer";
import SummaryTab from "@/components/SummaryTab";
import MindmapTab from "@/components/MindmapTab";
import QuizTab from "@/components/QuizTab";
import FlashcardTab from "@/components/FlashcardTab";
import FeynmanTab from "@/components/FeynmanTab";

type StudyTabKey = "summary" | "mindmap" | "quiz" | "flashcards" | "feynman";

export default function StudyWorkspacePage() {
  const params = useParams<{ docId: string }>();
  const docId = params.docId;

  const [doc, setDoc] = useState<StudyDocument | null>(null);
  const [summary, setSummary] = useState<SummaryRecord | null>(null);
  const [quizzes, setQuizzes] = useState<QuizSet[]>([]);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [feynmanSessions, setFeynmanSessions] = useState<FeynmanSession[]>([]);

  const [activeTab, setActiveTab] = useState<StudyTabKey>("summary");
  const [showLeftViewer, setShowLeftViewer] = useState(true);
  const [activePage, setActivePage] = useState(1);
  const [activeQuote, setActiveQuote] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [busySummary, setBusySummary] = useState(false);
  const [busyQuiz, setBusyQuiz] = useState(false);
  const [busySubmitQuiz, setBusySubmitQuiz] = useState(false);
  const [busyFlashcards, setBusyFlashcards] = useState(false);
  const [busyFeynman, setBusyFeynman] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadAll() {
      setLoading(true);
      setError("");
      try {
        const [docRes, sumRes, quizRes, cardRes, feynmanRes] = await Promise.all([
          api.getDocument(docId),
          api.getSummary(docId),
          api.listQuizzes(docId),
          api.listFlashcards(docId),
          api.listFeynmanSessions(docId),
        ]);
        if (!cancelled) {
          setDoc(docRes);
          setSummary(sumRes.summary);
          setQuizzes(quizRes.quizzes);
          setFlashcards(cardRes.flashcards);
          setFeynmanSessions(feynmanRes.sessions);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "학습 데이터를 불러오지 못했습니다.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (docId) loadAll();
    return () => {
      cancelled = true;
    };
  }, [docId]);

  const handleJumpToPage = (page: number, quote = "") => {
    const safePage = Math.max(1, Math.min(doc?.total_pages || 1, page));
    setShowLeftViewer(true);
    setActivePage(safePage);
    setActiveQuote(quote);
  };

  const handleGenerateSummary = async () => {
    setBusySummary(true);
    try {
      const res = await api.generateSummary(docId);
      setSummary(res);
    } catch (err) {
      alert(err instanceof Error ? err.message : "요약 생성 실패");
    } finally {
      setBusySummary(false);
    }
  };

  const handleGenerateQuiz = async (
    mcqCount: number,
    essayCount: number,
    difficulty: string
  ) => {
    setBusyQuiz(true);
    try {
      const newQuiz = await api.generateQuiz(docId, {
        mcq_count: mcqCount,
        essay_count: essayCount,
        difficulty,
      });
      setQuizzes((prev) => [newQuiz, ...prev]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "예상문제 생성 실패");
    } finally {
      setBusyQuiz(false);
    }
  };

  const handleSubmitQuiz = async (
    quizId: string,
    answers: Array<{ question_id: string; answer: string }>
  ) => {
    setBusySubmitQuiz(true);
    try {
      return await api.submitQuiz(quizId, answers);
    } finally {
      setBusySubmitQuiz(false);
    }
  };

  const handleGenerateFlashcards = async () => {
    setBusyFlashcards(true);
    try {
      const res = await api.generateFlashcards(docId, 8);
      setFlashcards((prev) => [...res.flashcards, ...prev]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "플래시카드 생성 실패");
    } finally {
      setBusyFlashcards(false);
    }
  };

  const handleReviewFlashcard = async (
    cardId: string,
    level: "again" | "hard" | "good" | "easy"
  ) => {
    const updated = await api.reviewFlashcard(cardId, level);
    setFlashcards((prev) => prev.map((c) => (c.id === cardId ? updated : c)));
  };

  const handleEvaluateFeynman = async (topic: string, userExplanation: string) => {
    setBusyFeynman(true);
    try {
      const created = await api.evaluateFeynman(docId, topic, userExplanation);
      setFeynmanSessions((prev) => [created, ...prev]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "파인만 평가 실패");
    } finally {
      setBusyFeynman(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="mx-auto max-w-xl px-4 py-12 text-center">
        <p className="text-sm font-bold text-rose-600">{error || "자료를 찾을 수 없습니다."}</p>
        <Link
          href="/"
          className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>대시보드로 돌아가기</span>
        </Link>
      </div>
    );
  }

  const tabs: Array<{ key: StudyTabKey; label: string; icon: typeof BookOpen }> = [
    { key: "summary", label: "요약 · 용어", icon: BookOpen },
    { key: "mindmap", label: "마인드맵", icon: Network },
    { key: "quiz", label: "예상문제", icon: HelpCircle },
    { key: "flashcards", label: "카드", icon: Layers },
    { key: "feynman", label: "파인만", icon: Brain },
  ];

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-[1600px] flex-col px-4 py-3 sm:px-6">
      {/* 상단 문서 타이틀 바 */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/"
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-600 hover:bg-slate-100"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[11px] font-bold text-teal-700">
                {doc.category}
              </span>
              <h1 className="truncate text-sm font-bold text-slate-900 sm:text-base">{doc.title}</h1>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowLeftViewer((prev) => !prev)}
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs transition hover:bg-slate-100"
        >
          {showLeftViewer ? (
            <>
              <PanelLeftClose className="h-3.5 w-3.5 text-teal-600" />
              <span>원본 자료 닫기 (전체 보기)</span>
            </>
          ) : (
            <>
              <PanelLeftOpen className="h-3.5 w-3.5 text-teal-600" />
              <span>원본 자료 열기</span>
            </>
          )}
        </button>
      </div>

      {/* 2단 Split View */}
      <div className="flex flex-1 flex-col gap-4 overflow-hidden lg:flex-row">
        {/* 좌측: 원본 문서 뷰어 (초기 44%, 우측 클릭 시 닫힘) */}
        {showLeftViewer && (
          <div className="h-[420px] min-w-0 shrink-0 overflow-hidden lg:h-full lg:w-[44%]">
            <DocumentViewer
              doc={doc}
              activePage={activePage}
              activeQuote={activeQuote}
              onPageChange={(p) => {
                setActivePage(p);
                setActiveQuote("");
              }}
            />
          </div>
        )}

        {/* 우측: 5대 AI 학습 스튜디오 (초기 56%, 클릭 시 좌측 닫히고 100% 확장) */}
        <div
          onClick={(e) => {
            const target = e.target as HTMLElement;
            if (target.closest("[data-keep-viewer='true']")) return;
            if (showLeftViewer) setShowLeftViewer(false);
          }}
          className="flex h-full min-w-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-slate-50"
        >
          {/* 탭 헤더 */}
          <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-bold transition ${
                    active
                      ? "bg-teal-600 text-white shadow-2xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* 탭 컨텐츠 */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5">
            {activeTab === "summary" && (
              <SummaryTab
                summary={summary}
                loading={busySummary}
                onGenerate={handleGenerateSummary}
                onJumpToPage={handleJumpToPage}
              />
            )}

            {activeTab === "mindmap" && (
              <MindmapTab
                mermaidCode={summary?.mindmap_mermaid || ""}
                onGenerateSummary={() => {
                  setActiveTab("summary");
                  handleGenerateSummary();
                }}
              />
            )}

            {activeTab === "quiz" && (
              <QuizTab
                quizzes={quizzes}
                generating={busyQuiz}
                submitting={busySubmitQuiz}
                onGenerateQuiz={handleGenerateQuiz}
                onSubmitQuiz={handleSubmitQuiz}
                onJumpToPage={handleJumpToPage}
              />
            )}

            {activeTab === "flashcards" && (
              <FlashcardTab
                cards={flashcards}
                generating={busyFlashcards}
                onGenerate={handleGenerateFlashcards}
                onReview={handleReviewFlashcard}
              />
            )}

            {activeTab === "feynman" && (
              <FeynmanTab
                docTitle={doc.title}
                sessions={feynmanSessions}
                evaluating={busyFeynman}
                onEvaluate={handleEvaluateFeynman}
                onJumpToPage={(p) => handleJumpToPage(p)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

