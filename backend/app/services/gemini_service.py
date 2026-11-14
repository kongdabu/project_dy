import json
import re
from typing import Optional
import httpx
from google import genai
from google.genai import types
from app.config import settings
from app.schemas.models import (
    EssayGradeOutput,
    FeynmanFeedbackOutput,
    FlashcardsOutput,
    QuizGeneratedOutput,
    SummaryOutput,
)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _extract_json_text(raw_text: str) -> str:
    """모델 응답에서 마크다운 코드 블록을 제거하고 순수 JSON 문자열만 추출"""
    text = (raw_text or "").strip()
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()
    return text


def _format_pages_context(pages: list[dict], max_chars: int = 180000) -> str:
    """페이지 번호가 포함된 학습 자료 컨텍스트 문자열 생성"""
    chunks: list[str] = []
    total_len = 0
    for p in pages:
        block = f"[Page {p.get('page', 1)}]\n{p.get('text', '')}\n"
        if total_len + len(block) > max_chars:
            chunks.append("\n... (이하 분량 제한으로 생략) ...")
            break
        chunks.append(block)
        total_len += len(block)
    return "\n".join(chunks)


class GeminiService:
    """OpenRouter(Qwen 등) 및 Google Gemini API를 지원하는 의학 학습 AI 엔진"""

    @staticmethod
    def _get_openrouter_api_key() -> str:
        api_key = (settings.openrouter_api_key or "").strip()
        if not api_key or "your_openrouter_api_key" in api_key:
            raise ValueError(
                "OpenRouter API 키가 설정되지 않았습니다. backend/.env 또는 Render.com의 OPENROUTER_API_KEY 환경변수를 설정해 주세요."
            )
        return api_key

    @staticmethod
    def _get_gemini_client(custom_api_key: Optional[str] = None) -> genai.Client:
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key or "your_gemini_api_key" in api_key:
            raise ValueError(
                "Gemini API 키가 설정되지 않았습니다. backend/.env 또는 Render.com의 GEMINI_API_KEY 환경변수를 설정해 주세요."
            )
        return genai.Client(api_key=api_key)

    def _generate_structured_openrouter(
        self,
        prompt: str,
        response_schema: type,
        temperature: float = 0.2,
    ):
        """OpenRouter Chat Completions API를 호출하여 JSON 스키마 기반 구조화 응답 생성"""
        api_key = self._get_openrouter_api_key()
        schema_json = json.dumps(response_schema.model_json_schema(), ensure_ascii=False)
        system_prompt = (
            "당신은 의학 교육 AI 어시스턴트입니다. 반드시 아래 JSON Schema를 정확히 준수하는 "
            "단일 JSON 객체만 출력하세요. 설명 문장이나 마크다운 코드블록(```)을 덧붙이지 마세요.\n\n"
            f"[JSON Schema]\n{schema_json}"
        )

        payload = {
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://medstudy-portal.local",
            "X-Title": "MedStudy Portal",
        }

        with httpx.Client(timeout=120.0) as client:
            res = client.post(OPENROUTER_API_URL, headers=headers, json=payload)

        if res.status_code >= 400:
            raise ValueError(f"OpenRouter API 호출 실패 ({res.status_code}): {res.text[:300]}")

        data = res.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter API 응답에 choices가 비어 있습니다.")

        message_content = (choices[0].get("message") or {}).get("content")
        if isinstance(message_content, list):
            # 멀티모달/파트 배열 응답 대응
            message_content = "".join(
                part.get("text", "") for part in message_content if isinstance(part, dict)
            )
        if not message_content or not isinstance(message_content, str):
            raise ValueError("OpenRouter API 응답 본문이 비어 있습니다.")

        cleaned = _extract_json_text(message_content)
        return response_schema.model_validate_json(cleaned)

    def _generate_structured(
        self,
        prompt: str,
        response_schema: type,
        custom_api_key: Optional[str] = None,
        temperature: float = 0.2,
    ):
        """Structured Output(JSON Schema) 기반 AI 호출 공통 헬퍼"""
        provider = (settings.ai_provider or "openrouter").strip().lower()
        if provider == "openrouter":
            return self._generate_structured_openrouter(
                prompt=prompt,
                response_schema=response_schema,
                temperature=temperature,
            )

        client = self._get_gemini_client(custom_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=temperature,
            ),
        )
        return response_schema.model_validate_json(response.text)

    def generate_summary_and_mindmap(
        self, pages: list[dict], title: str, custom_api_key: Optional[str] = None
    ) -> SummaryOutput:
        """핵심 요약 + 의학용어 쉬운 해설 + 근거 페이지 + AI 마인드맵 일괄 생성"""
        context = _format_pages_context(pages)
        prompt = f"""
당신은 의과대학 최고의 교수이자 의학 교육 전문가입니다.
아래 학습 자료('{title}')를 분석하여 의대생이 시험과 임상을 대비할 수 있도록 구조화된 결과를 JSON으로 생성하세요.

[요구사항]
1. overview: 자료 전체의 핵심 흐름과 목적을 3~5문장으로 명쾌하게 요약하세요.
2. key_points: 최소 4개 이상의 핵심 섹션(예: 병태생리/기전, 임상 양상, 진단 기준, 감별 진단, 치료 원칙 등 자료 성격에 맞게)으로 나누어 요약하세요.
   - 각 항목에는 시험에 꼭 나오는 High-Yield 포인트(clinical_pearl)를 포함하세요.
   - 각 항목마다 반드시 근거가 되는 원문 페이지 번호(page)와 원문 발췌 문장(quote)을 references에 정확히 기록하세요.
3. medical_terms: 본문에 등장하는 주요 전문 의학용어(최소 6개 이상)를 추출하세요.
   - simple_explanation은 의대 저학년도 바로 이해할 수 있도록 일상적인 비유와 쉬운 한국어로 풀어쓰세요.
   - mechanism에는 핵심 생리/병리 기전이나 임상적 의미를 적고, 처음 등장하는 page 번호를 기록하세요.
4. mindmap_mermaid: 자료의 핵심 개념과 기전, 진단/치료 흐름을 한눈에 볼 수 있는 유효한 Mermaid `flowchart TD` 코드를 작성하세요.
   - 노드 라벨에 괄호나 특수문자가 들어갈 경우 반드시 큰따옴표(`A["심근경색 (MI)"]`)로 감싸 문법 오류를 방지하세요.
   - HTML 태그(`<br>`)는 사용하지 마세요.

[학습 자료 원문]
{context}
"""
        return self._generate_structured(prompt, SummaryOutput, custom_api_key=custom_api_key)

    def generate_quiz(
        self,
        pages: list[dict],
        title: str,
        mcq_count: int,
        essay_count: int,
        difficulty: str,
        custom_api_key: Optional[str] = None,
    ) -> QuizGeneratedOutput:
        """4지선다(MCQ) 및 서술형(ESSAY) 예상문제 세트 생성"""
        context = _format_pages_context(pages)
        prompt = f"""
당신은 한국의사국가시험(KMLE) 및 의과대학 시험 출제위원입니다.
아래 학습 자료('{title}')를 바탕으로 난이도 '{difficulty}' 수준의 예상문제를 출제하세요.

[출제 문항 수]
- 4지선다 객관식(question_type: "MCQ"): 정확히 {mcq_count}문항
- 서술형 주관식(question_type: "ESSAY"): 정확히 {essay_count}문항

[문항별 작성 규칙]
1. MCQ(4지선다):
   - 임상 증례형 또는 핵심 기전 확인 문제로 출제하세요.
   - options 배열에 정확히 4개의 보기를 넣으세요 (번호 접두사 없이 보기 내용만 작성).
   - correct_answer에는 정답 보기 번호를 문자열 "1", "2", "3", "4" 중 하나로만 기입하세요.
   - keywords는 빈 배열 `[]`로 두세요.
2. ESSAY(서술형):
   - 핵심 기전 설명, 감별진단 근거, 치료 선택 이유 등을 묻는 문제로 출제하세요.
   - options는 빈 배열 `[]`로 두세요.
   - correct_answer에는 모범 답안을 작성하세요.
   - keywords에는 채점 시 반드시 포함되어야 할 핵심 의학 키워드 3~5개를 넣으세요.
3. 공통:
   - explanation에는 정답인 이유와 함께, MCQ의 경우 나머지 오답 선지가 왜 틀렸는지도 상세히 설명하세요.
   - source_reference에는 문제의 근거가 된 정확한 page 번호와 원문 발췌문(quote)을 기입하세요.

[학습 자료 원문]
{context}
"""
        return self._generate_structured(
            prompt, QuizGeneratedOutput, custom_api_key=custom_api_key, temperature=0.3
        )

    def grade_essay(
        self,
        question_text: str,
        model_answer: str,
        keywords: list[str],
        user_answer: str,
        custom_api_key: Optional[str] = None,
    ) -> EssayGradeOutput:
        """서술형 답안에 대한 AI 부분점수 채점 및 피드백"""
        prompt = f"""
당신은 의과대학 채점관입니다. 학생의 서술형 답안을 모범 답안 및 핵심 키워드와 비교하여 공정하게 채점하세요.

[문제]
{question_text}

[모범 답안]
{model_answer}

[핵심 채점 키워드]
{", ".join(keywords)}

[학생 답안]
{user_answer}

[채점 기준]
- 핵심 기전과 의학적 의미가 맞으면 표현이 달라도 점수를 부여하세요.
- score_percent가 60점 이상이면 is_correct를 true로 설정하세요.
- matched_keywords와 missing_keywords를 구분하고, feedback에 보완할 점을 친절히 적어주세요.
"""
        return self._generate_structured(prompt, EssayGradeOutput, custom_api_key=custom_api_key)

    def generate_flashcards(
        self, pages: list[dict], title: str, count: int = 8, custom_api_key: Optional[str] = None
    ) -> FlashcardsOutput:
        """Tikonote 스타일 자동 플래시카드 생성"""
        context = _format_pages_context(pages)
        prompt = f"""
당신은 의대생 능동적 인출(Active Recall) 학습 코치입니다.
아래 자료('{title}')에서 시험 직전 암기해야 할 핵심 개념, 의학용어, 약물 기전, 진단 기준을 추출하여 {count}개의 플래시카드를 만드세요.

[작성 규칙]
- front_text: 짧고 명확한 질문, 빈칸 문장, 또는 의학용어 (예: "심부전 환자에서 ACE 억제제의 핵심 작용 기전은?")
- back_text: 한눈에 들어오는 핵심 정답과 기전 요약 (2~3문장 이내)
- category_tag: 병태생리, 약리, 진단, 치료, 용어 중 하나

[학습 자료 원문]
{context}
"""
        return self._generate_structured(
            prompt, FlashcardsOutput, custom_api_key=custom_api_key, temperature=0.3
        )

    def evaluate_feynman(
        self,
        pages: list[dict],
        title: str,
        topic: str,
        user_explanation: str,
        custom_api_key: Optional[str] = None,
    ) -> FeynmanFeedbackOutput:
        """Tikonote 파인만 & 블러팅(Blurting) AI 튜터 평가"""
        context = _format_pages_context(pages)
        prompt = f"""
당신은 파인만 학습법(Feynman Technique)과 블러팅(Blurting) 기법을 지도하는 의대 AI 튜터입니다.
학생이 학습 자료('{title}')를 본 뒤, '{topic}' 주제에 대해 힌트 없이 기억나는 내용을 백지에 자유롭게 설명했습니다.
원본 자료와 대조하여 학생의 이해도를 정밀하게 진단해 주세요.

[학생의 블러팅 서술]
{user_explanation}

[요구사항]
- understanding_score: 원본 내용 대비 핵심 기전과 개념을 얼마나 정확히 인출했는지 0~100점으로 평가
- strengths: 학생이 정확히 짚어낸 핵심 개념 목록
- missing_concepts: 원본 자료에는 중요하게 나오지만 학생이 설명에서 빠뜨린 핵심 개념/기전
- misconceptions: 학생이 잘못 적었거나 혼동한 개념 (없으면 빈 배열)
- coach_summary: 격려와 함께 시험 대비를 위해 어떤 부분을 다시 연결해 암기해야 할지 요약 조언
- reference_page: 학생이 다시 복습해야 할 가장 관련 높은 원본 자료 페이지 번호

[학습 자료 원문]
{context}
"""
        return self._generate_structured(prompt, FeynmanFeedbackOutput, custom_api_key=custom_api_key)


gemini_service = GeminiService()
