# MedStudy Portal — 의대생 AI 학습 포털

수업자료·의학 논문·리포트를 업로드하면 **핵심 요약(의학용어 쉬운 해설 + 근거 페이지 링크)**, **AI 마인드맵**, **예상문제(4지선다·서술형 즉시 해설)**, **AI 플래시카드**, **파인만 & 블러팅 AI 튜터**, **학습 이력/오답노트**를 제공하는 웹 포털입니다.

## 아키텍처
- **Frontend**: Next.js (App Router, TypeScript, Tailwind CSS) → **Vercel** 배포
- **Backend**: Python FastAPI (`PyMuPDF`, `python-docx`, `python-pptx`, `google-genai`) → **Render** 배포
- **DB & Storage**: **Supabase** (PostgreSQL + Storage) *(로컬 개발 시 Supabase 미설정 상태에서도 JSON 로컬 폴백으로 즉시 실행 가능)*

## 1. Supabase 설정
1. Supabase 프로젝트 생성 후 SQL Editor에서 [supabase/schema.sql](supabase/schema.sql)을 실행합니다.
2. Project Settings → API에서 `Project URL`과 `service_role` (또는 `anon`) 키를 복사합니다.

## 2. Backend 실행 및 환경변수 설정 (.env / Render.com)
모든 API 키와 DB 접속 정보는 `backend/.env` (로컬) 또는 **Render.com Environment Variables**에 저장하여 사용합니다.

- 로컬 실행:
  1. `backend/.env` 파일에 `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` 입력
  2. 서버 실행:
     ```bash
     cd backend
     .venv/bin/uvicorn app.main:app --reload --port 8000
     ```
- Render.com 배포:
  - `backend/render.yaml`을 사용하여 Web Service를 생성하고, Render 대시보드의 **Environment** 탭에서 `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `ALLOWED_ORIGINS`를 등록합니다.

## 3. Frontend 실행 (Vercel 배포용)
```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000 (배포 시 Render URL)
npm install
npm run dev
```
- 브라우저에서 `http://localhost:3000`으로 접속합니다.
