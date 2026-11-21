"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { FileUp, Loader2, CheckCircle2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";

const CATEGORIES = ["일반의학", "해부학", "생리학", "병리학", "약리학", "내과학", "외과학"];

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("내과학");
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFileSelect = (selected: File | null) => {
    if (!selected) return;
    setFile(selected);
    if (!title) {
      setTitle(selected.name.replace(/\.[^/.]+$/, ""));
    }
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("업로드할 파일을 선택해 주세요.");
      return;
    }

    setUploading(true);
    setError("");
    try {
      const doc = await api.uploadDocument(file, title, category);
      router.push(`/study/${doc.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "업로드에 실패했습니다.");
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        <span>대시보드로 돌아가기</span>
      </Link>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs sm:p-8">
        <h1 className="text-xl font-bold text-slate-900">학습 자료 업로드</h1>
        <p className="mt-1 text-sm text-slate-500">
          수업 교안(PDF, PPTX), 의학 논문(PDF), 리포트(DOCX), 필기 노트(TXT, MD), 강의 녹음(MP3, M4A, WAV, WEBM, OGG)을 업로드하면 자동으로 색인·전사됩니다.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          {/* 드래그 앤 드롭 영역 */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              handleFileSelect(e.dataTransfer.files?.[0] || null);
            }}
            className={`flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition ${
              dragging
                ? "border-teal-500 bg-teal-50"
                : file
                  ? "border-teal-300 bg-teal-50/40"
                  : "border-slate-300 bg-slate-50 hover:border-slate-400"
            }`}
          >
            {file ? (
              <>
                <CheckCircle2 className="h-10 w-10 text-teal-600" />
                <p className="mt-2 text-sm font-bold text-slate-900">{file.name}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <label className="mt-3 cursor-pointer text-xs font-semibold text-teal-700 underline">
                  다른 파일 선택
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.pptx,.txt,.md,.mp3,.m4a,.wav,.webm,.ogg,audio/*"
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                  />
                </label>
              </>
            ) : (
              <>
                <FileUp className="h-10 w-10 text-slate-400" />
                <p className="mt-3 text-sm font-semibold text-slate-700">
                  파일을 여기에 끌어다 놓거나 클릭하여 선택하세요
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  지원 포맷: PDF, PPTX, DOCX, TXT, MD, MP3, M4A, WAV, WEBM, OGG
                </p>
                <label className="mt-4 cursor-pointer rounded-xl bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-xs ring-1 ring-slate-200 hover:bg-slate-50">
                  파일 찾아보기
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.pptx,.txt,.md,.mp3,.m4a,.wav,.webm,.ogg,audio/*"
                    className="hidden"
                    onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                  />
                </label>
              </>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700">자료 제목</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="예: 급성 심근경색 병태생리 및 치료"
                className="mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm focus:border-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700">과목 / 분류</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm focus:border-teal-500 focus:outline-none"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={uploading || !file}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-teal-600 py-3 text-sm font-bold text-white shadow-xs transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>
                  {/\.(mp3|m4a|wav|webm|ogg)$/i.test(file?.name || "")
                    ? "음성 전사(Gemini Audio STT) 및 저장 중... (잠시 기다려 주세요)"
                    : "문서 파싱 및 저장 중..."}
                </span>
              </>
            ) : (
              <span>업로드하고 학습 스튜디오 열기</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

