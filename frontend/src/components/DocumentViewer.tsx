"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, FileText, Quote, Eye } from "lucide-react";
import { resolveFileUrl } from "@/lib/api";
import type { StudyDocument } from "@/lib/types";

interface DocumentViewerProps {
  doc: StudyDocument;
  activePage: number;
  activeQuote: string;
  onPageChange: (page: number) => void;
}

export default function DocumentViewer({
  doc,
  activePage,
  activeQuote,
  onPageChange,
}: DocumentViewerProps) {
  const isPdf = doc.file_type.toLowerCase() === "pdf";
  const [viewMode, setViewMode] = useState<"pdf" | "text">(isPdf ? "pdf" : "text");

  const pages = doc.page_contents || [];
  const currentPageObj = pages.find((p) => p.page === activePage) || pages[0];
  const fileSrc = resolveFileUrl(doc.file_url);

  const highlightText = (text: string, quote: string) => {
    if (!quote || quote.length < 4) return text;
    const snippet = quote.slice(0, 30);
    const idx = text.indexOf(snippet);
    if (idx === -1) return text;
    return (
      <>
        {text.slice(0, idx)}
        <mark className="rounded bg-amber-200 px-1 py-0.5 text-slate-900">{text.slice(idx, idx + quote.length)}</mark>
        {text.slice(idx + quote.length)}
      </>
    );
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
      {/* 상단 컨트롤 바 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="h-4 w-4 shrink-0 text-teal-600" />
          <span className="truncate text-xs font-bold text-slate-800">{doc.file_name}</span>
        </div>

        <div className="flex items-center gap-2">
          {isPdf && (
            <div className="flex rounded-lg border border-slate-200 bg-white p-0.5 text-[11px] font-semibold">
              <button
                type="button"
                onClick={() => setViewMode("pdf")}
                className={`flex items-center gap-1 rounded-md px-2 py-1 ${
                  viewMode === "pdf" ? "bg-teal-600 text-white" : "text-slate-600"
                }`}
              >
                <Eye className="h-3 w-3" />
                <span>PDF</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode("text")}
                className={`rounded-md px-2 py-1 ${
                  viewMode === "text" ? "bg-teal-600 text-white" : "text-slate-600"
                }`}
              >
                텍스트
              </button>
            </div>
          )}

          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-xs">
            <button
              type="button"
              disabled={activePage <= 1}
              onClick={() => onPageChange(Math.max(1, activePage - 1))}
              className="rounded p-0.5 text-slate-600 hover:bg-slate-100 disabled:opacity-30"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="min-w-[54px] text-center font-semibold text-slate-700">
              {activePage} / {doc.total_pages}
            </span>
            <button
              type="button"
              disabled={activePage >= doc.total_pages}
              onClick={() => onPageChange(Math.min(doc.total_pages, activePage + 1))}
              className="rounded p-0.5 text-slate-600 hover:bg-slate-100 disabled:opacity-30"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* 근거 인용구 배너 */}
      {activeQuote && (
        <div className="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-900">
          <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
          <div>
            <span className="font-bold">p.{activePage} 근거 발췌: </span>
            <span className="italic">&ldquo;{activeQuote}&rdquo;</span>
          </div>
        </div>
      )}

      {/* 본문 뷰어 영역 */}
      <div className="flex-1 overflow-auto bg-slate-100">
        {viewMode === "pdf" && isPdf && fileSrc ? (
          <iframe
            key={`${fileSrc}-${activePage}`}
            src={`${fileSrc}#page=${activePage}`}
            className="h-full w-full border-0"
            title={doc.title}
          />
        ) : (
          <div className="p-5">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-xs font-bold text-teal-700">Page {activePage} 추출 텍스트</span>
                <span className="text-[11px] text-slate-400">{doc.file_type.toUpperCase()} 색인</span>
              </div>
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
                {currentPageObj?.text
                  ? highlightText(currentPageObj.text, activeQuote)
                  : "이 페이지에서 추출된 텍스트가 없습니다."}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

