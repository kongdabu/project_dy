-- 기존 Supabase 테이블에 Tikonote 통합 기능(마인드맵, 플래시카드, 파인만 튜터) 컬럼 및 테이블을 안전하게 추가하는 마이그레이션 SQL
-- Supabase SQL Editor에 복사하여 실행하세요.

-- 1. summaries 테이블에 mindmap_mermaid 컬럼 추가
alter table public.summaries
add column if not exists mindmap_mermaid text not null default '';

-- 2. quizzes 테이블에 difficulty 컬럼 추가
alter table public.quizzes
add column if not exists difficulty text not null default '임상응용';

-- 3. quiz_questions 테이블에 order_index 컬럼 추가
alter table public.quiz_questions
add column if not exists order_index int not null default 0;

-- 4. quiz_attempts 테이블에 total_questions 컬럼 추가
alter table public.quiz_attempts
add column if not exists total_questions int not null default 0;

-- 5. AI 플래시카드 테이블 생성
create table if not exists public.flashcards (
    id uuid primary key default uuid_generate_v4(),
    document_id uuid not null references public.documents(id) on delete cascade,
    front_text text not null,
    back_text text not null,
    category_tag text not null default '핵심개념',
    mastery_level text not null default 'again' check (mastery_level in ('again', 'hard', 'good', 'easy')),
    next_review_at timestamp with time zone default timezone('utc'::text, now()) not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 6. 파인만 & 블러팅 AI 튜터 세션 테이블 생성
create table if not exists public.feynman_sessions (
    id uuid primary key default uuid_generate_v4(),
    document_id uuid not null references public.documents(id) on delete cascade,
    topic text not null,
    user_explanation text not null,
    ai_feedback jsonb not null default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 7. 인덱스 및 RLS 정책
create index if not exists idx_flashcards_document_id on public.flashcards(document_id);
create index if not exists idx_feynman_sessions_document_id on public.feynman_sessions(document_id);

alter table public.flashcards enable row level security;
alter table public.feynman_sessions enable row level security;

do $$
begin
    if not exists (select 1 from pg_policies where tablename = 'flashcards' and policyname = 'Allow all access on flashcards') then
        create policy "Allow all access on flashcards" on public.flashcards for all using (true) with check (true);
    end if;
    if not exists (select 1 from pg_policies where tablename = 'feynman_sessions' and policyname = 'Allow all access on feynman_sessions') then
        create policy "Allow all access on feynman_sessions" on public.feynman_sessions for all using (true) with check (true);
    end if;
end $$;

-- 8. PostgREST 스키마 캐시 즉시 새로고침
notify pgrst, 'reload schema';

