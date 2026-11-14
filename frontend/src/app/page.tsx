"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FileText, Plus, Search, Trash2, BookOpenCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { StudyDocument } from "@/lib/types";

const CATEGORIES = ["전체", "일반의학", "해부학", "생리학", "병리학", "약리학", "내과학", "외과학"];

export default function DashboardPage() {
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [category, setCategory] = useState("전체");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchDocs = async (cat: string, q: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.listDocuments(cat, q);
      setDocuments(res.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs(category, query);
  }, [category]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchDocs(category, query);
  };

  const handleDelete = async (e: React.MouseEvent, docId: string, title: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm(`'${title}' 자료와 관련 요약/문제 이력을 모두 삭제할까요?`)) return;
    try {
      await api.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      alert(err instanceof Error ? err.message : "삭제 실패");
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* 상단 배너 */}
      <div className="flex flex-col justify-between gap-4 rounded-2xl bg-gradient-to-r from-teal-700 to-cyan-700 p-6 text-white shadow-sm sm:flex-row sm:items-center">
        <div>
          <div className="flex items-center gap-2 text-teal-100 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5" />
            <span>AI Medical Learning Studio</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">의대생 스마트 학습 포털</h1>
          <p className="mt-1 text-sm text-teal-50/90">
            강의록·논문을 올리면 의학용어 해설, 근거 링크 요약, AI 마인드맵, 4지선다·서술형 문제, 플래시카드, 파인만 튜터까지 한 번에 생성됩니다.
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-teal-800 shadow transition hover:bg-teal-50"
        >
          <Plus className="h-4 w-4" />
          <span>새 학습자료 올리기</span>
        </Link>
      </div>

      {/* 필터 & 검색 */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition ${
                category === cat
                  ? "bg-teal-600 text-white"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="자료 제목 검색..."
              className="w-56 rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm focus:border-teal-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            검색
          </button>
        </form>
      </div>

      {/* 자료 목록 */}
      {error && (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error} (백엔드 서버가 실행 중인지 확인해 주세요)
        </div>
      )}

      {loading ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 animate-pulse rounded-2xl border border-slate-200 bg-white p-5" />
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white py-16 text-center">
          <BookOpenCheck className="h-10 w-10 text-slate-300" />
          <p className="mt-3 text-base font-semibold text-slate-700">등록된 학습 자료가 없습니다</p>
          <p className="mt-1 text-sm text-slate-500">PDF 강의교안, 의학 논문, 리포트 등을 업로드해 학습을 시작해 보세요.</p>
          <Link
            href="/upload"
            className="mt-5 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-700"
          >
            첫 자료 업로드하기
          </Link>
        </div>
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <Link
              key={doc.id}
              href={`/study/${doc.id}`}
              className="group relative flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-xs transition hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span className="inline-flex items-center rounded-md bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700">
                    {doc.category}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, doc.id, doc.title)}
                    className="rounded-lg p-1.5 text-slate-400 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                    title="자료 삭제"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <h2 className="mt-3 line-clamp-2 text-base font-bold text-slate-900 group-hover:text-teal-700">
                  {doc.title}
                </h2>
                <p className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-500">
                  <FileText className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{doc.file_name}</span>
                </p>
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
                <span>
                  {doc.file_type.toUpperCase()} · {doc.total_pages}페이지
                </span>
                <span>{new Date(doc.created_at).toLocaleDateString("ko-KR")}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

