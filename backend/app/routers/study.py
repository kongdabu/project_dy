import logging
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.models import (
    FeynmanRequest,
    GenerateFlashcardsRequest,
    GenerateQuizRequest,
    ReviewFlashcardRequest,
    SubmitQuizRequest,
)
from app.services.auth_service import require_auth
from app.services.gemini_service import gemini_service
from app.services.rate_limiter import enforce_ai_rate_limit
from app.services.supabase_service import store

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api",
    tags=["study"],
    dependencies=[Depends(require_auth)],
)


def _get_doc_or_404(doc_id: str) -> dict:
    doc = store.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="학습 자료를 찾을 수 없습니다.")
    return doc


# ---------------- 1. 요약 + 의학용어 + AI 마인드맵 ----------------
@router.post("/study/{doc_id}/summarize", dependencies=[Depends(enforce_ai_rate_limit)])
def create_summary(doc_id: str):
    """자료 기반 핵심 요약, 의학용어 쉬운 해설, 근거 링크, Mermaid 마인드맵 생성"""
    doc = _get_doc_or_404(doc_id)
    try:
        result = gemini_service.generate_summary_and_mindmap(
            pages=doc.get("page_contents", []),
            title=doc["title"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("AI 요약 생성 실패 (doc_id=%s)", doc_id)
        raise HTTPException(status_code=500, detail="AI 요약 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    saved = store.save_summary(doc_id, result.model_dump())
    return saved


@router.get("/study/{doc_id}/summary")
def get_summary(doc_id: str):
    """저장된 최신 요약 및 마인드맵 조회"""
    _get_doc_or_404(doc_id)
    summary = store.get_latest_summary(doc_id)
    return {"summary": summary}


# ---------------- 2. 예상문제 (4지선다 + 서술형) ----------------
@router.post("/study/{doc_id}/quizzes", dependencies=[Depends(enforce_ai_rate_limit)])
def create_quiz(doc_id: str, body: GenerateQuizRequest):
    """자료 기반 4지선다 및 서술형 예상문제 세트 생성"""
    doc = _get_doc_or_404(doc_id)
    if body.mcq_count + body.essay_count == 0:
        raise HTTPException(status_code=400, detail="최소 1문항 이상 생성해야 합니다.")

    try:
        generated = gemini_service.generate_quiz(
            pages=doc.get("page_contents", []),
            title=doc["title"],
            mcq_count=body.mcq_count,
            essay_count=body.essay_count,
            difficulty=body.difficulty,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("예상문제 생성 실패 (doc_id=%s)", doc_id)
        raise HTTPException(status_code=500, detail="예상문제 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    questions_payload = [q.model_dump() for q in generated.questions]
    saved = store.create_quiz_with_questions(
        doc_id=doc_id,
        title=generated.title,
        difficulty=body.difficulty,
        questions=questions_payload,
    )
    return saved


@router.get("/study/{doc_id}/quizzes")
def list_doc_quizzes(doc_id: str):
    """자료에 속한 예상문제 세트 목록 조회"""
    _get_doc_or_404(doc_id)
    return {"quizzes": store.list_quizzes_for_document(doc_id)}


@router.post("/quizzes/{quiz_id}/submit", dependencies=[Depends(enforce_ai_rate_limit)])
def submit_quiz(quiz_id: str, body: SubmitQuizRequest):
    """문제 풀이 제출 -> 객관식 즉시 채점 + 서술형 AI 부분점수 채점 + 이력 저장"""
    quiz = store.get_quiz_with_questions(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="문제 세트를 찾을 수 없습니다.")

    answer_map = {item.question_id: item.answer.strip() for item in body.answers}
    evaluated_answers: list[dict] = []
    correct_count = 0

    for q in quiz["questions"]:
        user_ans = answer_map.get(q["id"], "")
        if q["question_type"] == "MCQ":
            is_correct = user_ans == str(q["correct_answer"]).strip()
            if is_correct:
                correct_count += 1
            evaluated_answers.append({
                "question_id": q["id"],
                "question_type": "MCQ",
                "user_answer": user_ans,
                "correct_answer": q["correct_answer"],
                "is_correct": is_correct,
                "explanation": q["explanation"],
                "source_reference": q.get("source_reference", {}),
            })
        else:
            keywords = q.get("keywords") or []
            try:
                grade = gemini_service.grade_essay(
                    question_text=q["question_text"],
                    model_answer=q["correct_answer"],
                    keywords=keywords,
                    user_answer=user_ans or "(미작성)",
                ).model_dump()
            except Exception:
                logger.warning("서술형 AI 채점 폴백 사용 (question_id=%s)", q["id"])
                matched = [kw for kw in keywords if kw.lower() in user_ans.lower()]
                missing = [kw for kw in keywords if kw not in matched]
                ratio = int((len(matched) / len(keywords)) * 100) if keywords else (100 if user_ans else 0)
                grade = {
                    "is_correct": ratio >= 50,
                    "score_percent": ratio,
                    "matched_keywords": matched,
                    "missing_keywords": missing,
                    "feedback": "핵심 키워드 포함 여부를 기준으로 자동 채점되었습니다.",
                }

            if grade["is_correct"]:
                correct_count += 1

            evaluated_answers.append({
                "question_id": q["id"],
                "question_type": "ESSAY",
                "user_answer": user_ans,
                "correct_answer": q["correct_answer"],
                "is_correct": grade["is_correct"],
                "score_percent": grade["score_percent"],
                "matched_keywords": grade["matched_keywords"],
                "missing_keywords": grade["missing_keywords"],
                "ai_feedback": grade["feedback"],
                "explanation": q["explanation"],
                "source_reference": q.get("source_reference", {}),
            })

    total_q = len(quiz["questions"])
    attempt = store.save_quiz_attempt({
        "quiz_id": quiz_id,
        "user_answers": evaluated_answers,
        "score": correct_count,
        "total_questions": total_q,
    })
    return {
        "attempt_id": attempt["id"],
        "score": correct_count,
        "total_questions": total_q,
        "results": evaluated_answers,
    }


# ---------------- 3. AI 플래시카드 ----------------
@router.post("/study/{doc_id}/flashcards", dependencies=[Depends(enforce_ai_rate_limit)])
def create_flashcards(doc_id: str, body: GenerateFlashcardsRequest):
    """자료 기반 AI 플래시카드 자동 생성"""
    doc = _get_doc_or_404(doc_id)
    try:
        generated = gemini_service.generate_flashcards(
            pages=doc.get("page_contents", []),
            title=doc["title"],
            count=body.count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("플래시카드 생성 실패 (doc_id=%s)", doc_id)
        raise HTTPException(status_code=500, detail="플래시카드 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    saved = store.create_flashcards(doc_id, [c.model_dump() for c in generated.cards])
    return {"flashcards": saved}


@router.get("/study/{doc_id}/flashcards")
def list_flashcards(doc_id: str):
    """자료에 속한 플래시카드 목록 조회"""
    _get_doc_or_404(doc_id)
    return {"flashcards": store.list_flashcards(doc_id)}


@router.patch("/flashcards/{card_id}/review")
def review_flashcard(card_id: str, body: ReviewFlashcardRequest):
    """플래시카드 숙련도 업데이트"""
    updated = store.update_flashcard_mastery(card_id, body.mastery_level)
    if not updated:
        raise HTTPException(status_code=404, detail="플래시카드를 찾을 수 없습니다.")
    return updated


# ---------------- 4. 파인만 & 블러팅 AI 튜터 ----------------
@router.post("/study/{doc_id}/feynman", dependencies=[Depends(enforce_ai_rate_limit)])
def evaluate_feynman(doc_id: str, body: FeynmanRequest):
    """파인만/블러팅 백지 인출 서술 평가 및 피드백"""
    doc = _get_doc_or_404(doc_id)
    if not body.user_explanation.strip():
        raise HTTPException(status_code=400, detail="서술 내용을 입력해 주세요.")
    try:
        feedback = gemini_service.evaluate_feynman(
            pages=doc.get("page_contents", []),
            title=doc["title"],
            topic=body.topic,
            user_explanation=body.user_explanation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception("파인만 평가 실패 (doc_id=%s)", doc_id)
        raise HTTPException(status_code=500, detail="파인만 평가 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    saved = store.save_feynman_session(
        doc_id=doc_id,
        topic=body.topic,
        user_explanation=body.user_explanation,
        ai_feedback=feedback.model_dump(),
    )
    return saved


@router.get("/study/{doc_id}/feynman")
def list_feynman_sessions(doc_id: str):
    """자료에 속한 파인만/블러팅 평가 이력 조회"""
    _get_doc_or_404(doc_id)
    return {"sessions": store.list_feynman_sessions(doc_id)}
