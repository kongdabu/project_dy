from typing import Literal
from pydantic import BaseModel, Field


class PageContent(BaseModel):
    """문서의 페이지별 추출 텍스트"""

    page: int
    text: str


class SourceReference(BaseModel):
    """원본 자료 근거 위치"""

    page: int = Field(description="근거가 위치한 원본 문서 페이지 번호 (1부터 시작)")
    quote: str = Field(description="원본 문서에서 발췌한 핵심 근거 문장 (20~80자 내외)")


class KeyPoint(BaseModel):
    """핵심 요약 항목"""

    section: str = Field(description="주제 또는 섹션 제목 (예: 병태생리, 임상양상, 진단기준, 치료원칙)")
    summary: str = Field(description="의대생 시험 대비 관점의 핵심 요약 내용")
    clinical_pearl: str = Field(default="", description="시험 및 임상에서 반드시 기억할 핵심 포인트(High-Yield Pearl)")
    references: list[SourceReference] = Field(default_factory=list, description="근거 자료 위치 목록")


class MedicalTerm(BaseModel):
    """의학용어 쉬운 해설"""

    term: str = Field(description="의학용어 원어 또는 한글명 (예: 심근경색 (Myocardial Infarction))")
    simple_explanation: str = Field(description="의대 저학년이나 일반인도 직관적으로 이해할 수 있는 쉬운 비유와 설명")
    mechanism: str = Field(default="", description="핵심 기전 또는 임상적 의미")
    page: int = Field(default=1, description="용어가 처음 등장하는 페이지 번호")


class SummaryOutput(BaseModel):
    """Gemini 요약 + 마인드맵 Structured Output 스키마"""

    overview: str = Field(description="전체 자료를 3~5문장으로 압축한 핵심 개요")
    key_points: list[KeyPoint] = Field(description="구조화된 핵심 요약 목록 (최소 4개 이상)")
    medical_terms: list[MedicalTerm] = Field(description="본문에 등장한 주요 의학용어 및 쉬운 해설 목록")
    mindmap_mermaid: str = Field(
        description="병태생리, 기전, 진단/치료 흐름을 시각화한 유효한 Mermaid flowchart TD 코드 (예: flowchart TD\\n A[\"주제\"] --> B[\"세부1\"])"
    )


class QuizQuestionGenerated(BaseModel):
    """Gemini가 생성하는 단일 예상문제 스키마"""

    question_type: Literal["MCQ", "ESSAY"] = Field(description="MCQ(4지선다) 또는 ESSAY(서술형)")
    question_text: str = Field(description="문제 지문 (임상 증례 또는 개념 확인 문제)")
    options: list[str] = Field(default_factory=list, description="MCQ일 경우 4개의 보기 텍스트, ESSAY일 경우 빈 배열")
    correct_answer: str = Field(description="MCQ일 경우 정답 보기 번호('1','2','3','4' 중 하나), ESSAY일 경우 모범 답안")
    keywords: list[str] = Field(default_factory=list, description="ESSAY일 경우 반드시 포함되어야 할 핵심 채점 키워드 목록")
    explanation: str = Field(description="정답 근거 및 오답 선지 분석을 포함한 상세 해설")
    source_reference: SourceReference = Field(description="이 문제의 근거가 된 원본 문서 페이지 및 인용구")


class QuizGeneratedOutput(BaseModel):
    """Gemini 예상문제 세트 Structured Output 스키마"""

    title: str = Field(description="생성된 예상문제 세트의 제목")
    questions: list[QuizQuestionGenerated]


class GenerateQuizRequest(BaseModel):
    """예상문제 생성 요청 바디"""

    mcq_count: int = Field(default=3, ge=0, le=10, description="4지선다 문항 수")
    essay_count: int = Field(default=2, ge=0, le=5, description="서술형 문항 수")
    difficulty: str = Field(default="임상응용", description="난이도 (기초개념 / 임상응용 / 국가고시실전)")


class EssayGradeOutput(BaseModel):
    """서술형 답안 AI 채점 결과"""

    is_correct: bool = Field(description="핵심 개념을 충족했는지 여부")
    score_percent: int = Field(ge=0, le=100, description="0~100점 환산 점수")
    matched_keywords: list[str] = Field(default_factory=list, description="답안에 포함된 핵심 키워드")
    missing_keywords: list[str] = Field(default_factory=list, description="답안에 누락된 핵심 키워드")
    feedback: str = Field(description="학생 답안에 대한 구체적인 강점 및 보완 피드백")


class UserAnswerItem(BaseModel):
    """사용자가 제출한 단일 문항 답안"""

    question_id: str
    answer: str


class SubmitQuizRequest(BaseModel):
    """문제 풀이 제출 요청 바디"""

    answers: list[UserAnswerItem]


class FlashcardGenerated(BaseModel):
    """단일 AI 플래시카드 스키마"""

    front_text: str = Field(description="앞면: 암기할 의학용어, 기전 질문, 또는 빈칸 문제")
    back_text: str = Field(description="뒷면: 명확한 정답 및 핵심 암기 포인트")
    category_tag: str = Field(default="핵심개념", description="분류 태그 (예: 병태생리, 약리, 진단, 치료)")


class FlashcardsOutput(BaseModel):
    """Gemini 플래시카드 목록 스키마"""

    cards: list[FlashcardGenerated]


class GenerateFlashcardsRequest(BaseModel):
    """플래시카드 생성 요청 바디"""

    count: int = Field(default=8, ge=3, le=20)


class ReviewFlashcardRequest(BaseModel):
    """플래시카드 숙련도 업데이트 요청"""

    mastery_level: Literal["again", "hard", "good", "easy"]


class FeynmanRequest(BaseModel):
    """파인만 & 블러팅 AI 튜터 요청"""

    topic: str = Field(description="사용자가 설명하고자 하는 주제 또는 개념")
    user_explanation: str = Field(description="단서 없이 사용자가 직접 서술한 내용(블러팅)")


class FeynmanFeedbackOutput(BaseModel):
    """파인만 AI 튜터 평가 결과"""

    understanding_score: int = Field(ge=0, le=100, description="이해도 점수 (0~100)")
    strengths: list[str] = Field(description="정확하게 이해하고 설명한 핵심 포인트")
    missing_concepts: list[str] = Field(description="자료에는 있으나 설명에서 누락된 중요 기전/개념")
    misconceptions: list[str] = Field(default_factory=list, description="잘못 이해하고 있거나 부정확한 부분")
    coach_summary: str = Field(description="의대생 선배/교수님 톤의 따뜻하고 명쾌한 교정 피드백")
    reference_page: int = Field(default=1, description="복습이 필요한 원본 자료 페이지")
