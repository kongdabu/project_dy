export interface PageContent {
  page: number;
  text: string;
}

export interface StudyDocument {
  id: string;
  title: string;
  category: string;
  file_name: string;
  file_url: string;
  file_type: string;
  total_pages: number;
  page_contents?: PageContent[];
  created_at: string;
}

export interface SourceReference {
  page: number;
  quote: string;
}

export interface KeyPoint {
  section: string;
  summary: string;
  clinical_pearl?: string;
  references: SourceReference[];
}

export interface MedicalTerm {
  term: string;
  simple_explanation: string;
  mechanism?: string;
  page: number;
}

export interface SummaryRecord {
  id: string;
  document_id: string;
  overview: string;
  key_points: KeyPoint[];
  medical_terms: MedicalTerm[];
  mindmap_mermaid: string;
  created_at: string;
}

export interface QuizQuestion {
  id: string;
  quiz_id: string;
  order_index: number;
  question_type: "MCQ" | "ESSAY";
  question_text: string;
  options: string[];
  correct_answer: string;
  keywords: string[];
  explanation: string;
  source_reference: SourceReference;
}

export interface QuizSet {
  id: string;
  document_id: string;
  title: string;
  difficulty: string;
  created_at: string;
  questions: QuizQuestion[];
}

export interface QuizSubmitResultItem {
  question_id: string;
  question_type: "MCQ" | "ESSAY";
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score_percent?: number;
  matched_keywords?: string[];
  missing_keywords?: string[];
  ai_feedback?: string;
  explanation: string;
  source_reference: SourceReference;
}

export interface QuizSubmitResponse {
  attempt_id: string;
  score: number;
  total_questions: number;
  results: QuizSubmitResultItem[];
}

export interface Flashcard {
  id: string;
  document_id: string;
  front_text: string;
  back_text: string;
  category_tag: string;
  mastery_level: "again" | "hard" | "good" | "easy";
  next_review_at: string;
  created_at: string;
}

export interface FeynmanFeedback {
  understanding_score: number;
  strengths: string[];
  missing_concepts: string[];
  misconceptions: string[];
  coach_summary: string;
  reference_page: number;
}

export interface FeynmanSession {
  id: string;
  document_id: string;
  topic: string;
  user_explanation: string;
  ai_feedback: FeynmanFeedback;
  created_at: string;
}

export interface HistoryResponse {
  documents_count: number;
  attempts: Array<{
    id: string;
    quiz_id: string;
    quiz_title: string;
    difficulty: string;
    document_id: string;
    document_title: string;
    category: string;
    score: number;
    total_questions: number;
    attempted_at: string;
  }>;
  wrong_questions: Array<
    QuizQuestion & {
      document_id: string;
      document_title: string;
      last_user_answer: string;
    }
  >;
  review_flashcards: Flashcard[];
  feynman_sessions: FeynmanSession[];
}

