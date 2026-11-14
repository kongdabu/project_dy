import type {
  FeynmanSession,
  Flashcard,
  HistoryResponse,
  QuizSet,
  QuizSubmitResponse,
  StudyDocument,
  SummaryRecord,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `요청 실패 (${res.status})`;
    try {
      const errData = await res.json();
      detail = errData.detail || detail;
    } catch {
      // JSON 파싱 실패 시 기본 메시지 사용
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function resolveFileUrl(fileUrl: string): string {
  if (!fileUrl) return "";
  if (fileUrl.startsWith("http://") || fileUrl.startsWith("https://")) {
    return fileUrl;
  }
  return `${API_BASE_URL}${fileUrl}`;
}

export const api = {
  // 자료 관리
  uploadDocument: async (file: File, title: string, category: string): Promise<StudyDocument> => {
    const formData = new FormData();
    formData.append("file", file);
    if (title.trim()) formData.append("title", title.trim());
    formData.append("category", category);
    return request<StudyDocument>("/api/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  listDocuments: (category?: string, q?: string) => {
    const params = new URLSearchParams();
    if (category && category !== "전체") params.set("category", category);
    if (q) params.set("q", q);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<{ documents: StudyDocument[] }>(`/api/documents${qs}`);
  },

  getDocument: (docId: string) => request<StudyDocument>(`/api/documents/${docId}`),

  deleteDocument: (docId: string) =>
    request<{ deleted: boolean }>(`/api/documents/${docId}`, { method: "DELETE" }),

  // 요약 & 마인드맵
  generateSummary: (docId: string) =>
    request<SummaryRecord>(`/api/study/${docId}/summarize`, { method: "POST" }),

  getSummary: (docId: string) =>
    request<{ summary: SummaryRecord | null }>(`/api/study/${docId}/summary`),

  // 예상문제
  generateQuiz: (
    docId: string,
    payload: { mcq_count: number; essay_count: number; difficulty: string }
  ) =>
    request<QuizSet>(`/api/study/${docId}/quizzes`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listQuizzes: (docId: string) =>
    request<{ quizzes: QuizSet[] }>(`/api/study/${docId}/quizzes`),

  submitQuiz: (quizId: string, answers: Array<{ question_id: string; answer: string }>) =>
    request<QuizSubmitResponse>(`/api/quizzes/${quizId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  // 플래시카드
  generateFlashcards: (docId: string, count = 8) =>
    request<{ flashcards: Flashcard[] }>(`/api/study/${docId}/flashcards`, {
      method: "POST",
      body: JSON.stringify({ count }),
    }),

  listFlashcards: (docId: string) =>
    request<{ flashcards: Flashcard[] }>(`/api/study/${docId}/flashcards`),

  reviewFlashcard: (cardId: string, mastery_level: "again" | "hard" | "good" | "easy") =>
    request<Flashcard>(`/api/flashcards/${cardId}/review`, {
      method: "PATCH",
      body: JSON.stringify({ mastery_level }),
    }),

  // 파인만 & 블러팅
  evaluateFeynman: (docId: string, topic: string, user_explanation: string) =>
    request<FeynmanSession>(`/api/study/${docId}/feynman`, {
      method: "POST",
      body: JSON.stringify({ topic, user_explanation }),
    }),

  listFeynmanSessions: (docId: string) =>
    request<{ sessions: FeynmanSession[] }>(`/api/study/${docId}/feynman`),

  // 이력 관리
  getHistory: () => request<HistoryResponse>("/api/history"),
};
