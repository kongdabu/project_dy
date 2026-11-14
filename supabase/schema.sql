-- 의대생 학습 포털 (MedStudy Portal) Supabase 스키마
-- Supabase SQL Editor에 복사하여 실행하세요.

-- UUID 확장 활성화
create extension if not exists "uuid-ossp";

-- 1. 학습 자료 테이블
create table if not exists public.documents (
    id uuid primary key default uuid_generate_v4(),
    title text not null,
    category text not null default '일반의학',
    file_name text not null,
    file_url text,
    file_type text not null,
    total_pages int not null default 1,
    page_contents jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. 핵심 요약 및 의학용어 해설 테이블
create table if not exists public.summaries (
    id uuid primary key default uuid_generate_v4(),
    document_id uuid not null references public.documents(id) on delete cascade,
    overview text not null,
    key_points jsonb not null default '[]'::jsonb,
    medical_terms jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. 예상문제 세트 테이블
create table if not exists public.quizzes (
    id uuid primary key default uuid_generate_v4(),
    document_id uuid not null references public.documents(id) on delete cascade,
    title text not null,
    difficulty text not null default '임상응용',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 4. 예상문제 문항 테이블 (4지선다 MCQ / 서술형 ESSAY)
create table if not exists public.quiz_questions (
    id uuid primary key default uuid_generate_v4(),
    quiz_id uuid not null references public.quizzes(id) on delete cascade,
    order_index int not null default 0,
    question_type text not null check (question_type in ('MCQ', 'ESSAY')),
    question_text text not null,
    options jsonb default '[]'::jsonb,
    correct_answer text not null,
    keywords jsonb default '[]'::jsonb,
    explanation text not null,
    source_reference jsonb not null default '{}'::jsonb
);

-- 5. 문제 풀이 이력 테이블
create table if not exists public.quiz_attempts (
    id uuid primary key default uuid_generate_v4(),
    quiz_id uuid not null references public.quizzes(id) on delete cascade,
    user_answers jsonb not null default '[]'::jsonb,
    score int not null default 0,
    total_questions int not null default 0,
    attempted_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 인덱스 생성
create index if not exists idx_summaries_document_id on public.summaries(document_id);
create index if not exists idx_quizzes_document_id on public.quizzes(document_id);
create index if not exists idx_quiz_questions_quiz_id on public.quiz_questions(quiz_id);
create index if not exists idx_quiz_attempts_quiz_id on public.quiz_attempts(quiz_id);

-- RLS(Row Level Security) 설정: 간이 포털 초기 구성을 위해 전체 접근 허용 (추후 Supabase Auth 연동 시 auth.uid() 기준으로 제한 가능)
alter table public.documents enable row level security;
alter table public.summaries enable row level security;
alter table public.quizzes enable row level security;
alter table public.quiz_questions enable row level security;
alter table public.quiz_attempts enable row level security;

create policy "Allow all access on documents" on public.documents for all using (true) with check (true);
create policy "Allow all access on summaries" on public.summaries for all using (true) with check (true);
create policy "Allow all access on quizzes" on public.quizzes for all using (true) with check (true);
create policy "Allow all access on quiz_questions" on public.quiz_questions for all using (true) with check (true);
create policy "Allow all access on quiz_attempts" on public.quiz_attempts for all using (true) with check (true);

-- Storage 버킷 생성 (원본 PDF/문서 저장용)
insert into storage.buckets (id, name, public)
values ('study-materials', 'study-materials', true)
on conflict (id) do nothing;

-- Storage 정책 설정
create policy "Public Access study-materials" on storage.objects
for all using (bucket_id = 'study-materials') with check (bucket_id = 'study-materials');

