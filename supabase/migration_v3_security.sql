-- 보안 강화 마이그레이션 (P1): DB 전체 허용 정책 제거 및 Storage 버킷 비공개 전환
-- Supabase SQL Editor에 복사하여 실행하세요.
-- (백엔드 FastAPI가 service_role 키로만 DB/Storage에 접근하므로 anon 직접 접근을 원천 차단합니다.)

-- 1. 기존 전체 허용(using true) RLS 정책 모두 제거
drop policy if exists "Allow all access on documents" on public.documents;
drop policy if exists "Allow all access on summaries" on public.summaries;
drop policy if exists "Allow all access on quizzes" on public.quizzes;
drop policy if exists "Allow all access on quiz_questions" on public.quiz_questions;
drop policy if exists "Allow all access on quiz_attempts" on public.quiz_attempts;
drop policy if exists "Allow all access on flashcards" on public.flashcards;
drop policy if exists "Allow all access on feynman_sessions" on public.feynman_sessions;

-- 2. RLS 활성화 유지 (정책이 없으면 anon/authenticated 역할은 모든 행 접근 차단, service_role만 접근 가능)
alter table public.documents enable row level security;
alter table public.summaries enable row level security;
alter table public.quizzes enable row level security;
alter table public.quiz_questions enable row level security;
alter table public.quiz_attempts enable row level security;
alter table public.flashcards enable row level security;
alter table public.feynman_sessions enable row level security;

-- 3. Storage 버킷을 비공개(public = false)로 전환하고 기존 공개 정책 제거
update storage.buckets
set public = false
where id = 'study-materials';

drop policy if exists "Public Access study-materials" on storage.objects;

-- 4. PostgREST 스키마 캐시 새로고침
notify pgrst, 'reload schema';

