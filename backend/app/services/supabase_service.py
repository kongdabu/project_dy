import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
from supabase import create_client, Client
from app.config import settings

# Supabase 미설정 시 로컬 개발용 폴백 저장소 경로
LOCAL_STORE_DIR = Path(__file__).resolve().parent.parent.parent / "_local_store"
LOCAL_FILES_DIR = LOCAL_STORE_DIR / "files"
LOCAL_DB_FILE = LOCAL_STORE_DIR / "db.json"


class DataStoreService:
    """Supabase DB/Storage 연동 및 로컬 개발용 JSON 폴백 저장소"""

    def __init__(self) -> None:
        self._client: Optional[Client] = None
        if settings.is_supabase_configured:
            self._client = create_client(settings.supabase_url, settings.supabase_key)
        else:
            LOCAL_FILES_DIR.mkdir(parents=True, exist_ok=True)
            if not LOCAL_DB_FILE.exists():
                self._save_local_db({
                    "documents": [],
                    "summaries": [],
                    "quizzes": [],
                    "quiz_questions": [],
                    "quiz_attempts": [],
                    "flashcards": [],
                    "feynman_sessions": [],
                })

    @property
    def is_supabase(self) -> bool:
        return self._client is not None

    def _load_local_db(self) -> dict[str, list[dict]]:
        with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_local_db(self, data: dict[str, list[dict]]) -> None:
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ---------------- 파일 업로드 ----------------
    def upload_file(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """파일을 Supabase Storage 또는 로컬 디렉토리에 저장하고 접근 URL/경로 반환"""
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        if self._client:
            self._client.storage.from_(settings.supabase_bucket).upload(
                path=safe_name,
                file=file_bytes,
                file_options={"content-type": content_type},
            )
            return self._client.storage.from_(settings.supabase_bucket).get_public_url(safe_name)

        local_path = LOCAL_FILES_DIR / safe_name
        local_path.write_bytes(file_bytes)
        return f"/api/documents/local-file/{safe_name}"

    def get_local_file_path(self, safe_name: str) -> Optional[Path]:
        path = (LOCAL_FILES_DIR / safe_name).resolve()
        if path.parent == LOCAL_FILES_DIR.resolve() and path.exists():
            return path
        return None

    # ---------------- Documents ----------------
    def create_document(self, doc_data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "created_at": self._now_iso(),
            **doc_data,
        }
        if self._client:
            res = self._client.table("documents").insert(record).execute()
            return res.data[0]
        db = self._load_local_db()
        db["documents"].insert(0, record)
        self._save_local_db(db)
        return record

    def list_documents(self, category: Optional[str] = None, query: Optional[str] = None) -> list[dict[str, Any]]:
        if self._client:
            q = self._client.table("documents").select(
                "id, title, category, file_name, file_url, file_type, total_pages, created_at"
            ).order("created_at", desc=True)
            if category and category != "전체":
                q = q.eq("category", category)
            if query:
                q = q.ilike("title", f"%{query}%")
            return q.execute().data

        db = self._load_local_db()
        docs = db["documents"]
        if category and category != "전체":
            docs = [d for d in docs if d.get("category") == category]
        if query:
            q_lower = query.lower()
            docs = [d for d in docs if q_lower in d.get("title", "").lower()]
        return [
            {k: v for k, v in d.items() if k != "page_contents"}
            for d in docs
        ]

    def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        if self._client:
            res = self._client.table("documents").select("*").eq("id", doc_id).execute()
            return res.data[0] if res.data else None
        db = self._load_local_db()
        return next((d for d in db["documents"] if d["id"] == doc_id), None)

    def delete_document(self, doc_id: str) -> bool:
        if self._client:
            self._client.table("documents").delete().eq("id", doc_id).execute()
            return True
        db = self._load_local_db()
        db["documents"] = [d for d in db["documents"] if d["id"] != doc_id]
        db["summaries"] = [s for s in db["summaries"] if s["document_id"] != doc_id]
        quiz_ids = {q["id"] for q in db["quizzes"] if q["document_id"] == doc_id}
        db["quizzes"] = [q for q in db["quizzes"] if q["document_id"] != doc_id]
        db["quiz_questions"] = [qq for qq in db["quiz_questions"] if qq["quiz_id"] not in quiz_ids]
        db["quiz_attempts"] = [qa for qa in db["quiz_attempts"] if qa["quiz_id"] not in quiz_ids]
        db["flashcards"] = [fc for fc in db["flashcards"] if fc["document_id"] != doc_id]
        db["feynman_sessions"] = [fs for fs in db["feynman_sessions"] if fs["document_id"] != doc_id]
        self._save_local_db(db)
        return True

    # ---------------- Summaries ----------------
    def save_summary(self, doc_id: str, summary_data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "created_at": self._now_iso(),
            **summary_data,
        }
        if self._client:
            res = self._client.table("summaries").insert(record).execute()
            return res.data[0]
        db = self._load_local_db()
        db["summaries"].insert(0, record)
        self._save_local_db(db)
        return record

    def get_latest_summary(self, doc_id: str) -> Optional[dict[str, Any]]:
        if self._client:
            res = (
                self._client.table("summaries")
                .select("*")
                .eq("document_id", doc_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        db = self._load_local_db()
        return next((s for s in db["summaries"] if s["document_id"] == doc_id), None)

    # ---------------- Quizzes ----------------
    def create_quiz_with_questions(
        self, doc_id: str, title: str, difficulty: str, questions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        quiz_id = str(uuid.uuid4())
        quiz_record = {
            "id": quiz_id,
            "document_id": doc_id,
            "title": title,
            "difficulty": difficulty,
            "created_at": self._now_iso(),
        }
        q_records = []
        for idx, q in enumerate(questions):
            q_records.append({
                "id": str(uuid.uuid4()),
                "quiz_id": quiz_id,
                "order_index": idx,
                **q,
            })

        if self._client:
            self._client.table("quizzes").insert(quiz_record).execute()
            if q_records:
                self._client.table("quiz_questions").insert(q_records).execute()
        else:
            db = self._load_local_db()
            db["quizzes"].insert(0, quiz_record)
            db["quiz_questions"].extend(q_records)
            self._save_local_db(db)

        return {**quiz_record, "questions": q_records}

    def list_quizzes_for_document(self, doc_id: str) -> list[dict[str, Any]]:
        if self._client:
            quizzes = (
                self._client.table("quizzes")
                .select("*")
                .eq("document_id", doc_id)
                .order("created_at", desc=True)
                .execute()
                .data
            )
            for qz in quizzes:
                qs = (
                    self._client.table("quiz_questions")
                    .select("*")
                    .eq("quiz_id", qz["id"])
                    .order("order_index")
                    .execute()
                    .data
                )
                qz["questions"] = qs
            return quizzes

        db = self._load_local_db()
        quizzes = [q for q in db["quizzes"] if q["document_id"] == doc_id]
        result = []
        for qz in quizzes:
            qs = sorted(
                [qq for qq in db["quiz_questions"] if qq["quiz_id"] == qz["id"]],
                key=lambda x: x.get("order_index", 0),
            )
            result.append({**qz, "questions": qs})
        return result

    def get_quiz_with_questions(self, quiz_id: str) -> Optional[dict[str, Any]]:
        if self._client:
            res = self._client.table("quizzes").select("*").eq("id", quiz_id).execute()
            if not res.data:
                return None
            qz = res.data[0]
            qs = (
                self._client.table("quiz_questions")
                .select("*")
                .eq("quiz_id", quiz_id)
                .order("order_index")
                .execute()
                .data
            )
            return {**qz, "questions": qs}

        db = self._load_local_db()
        qz = next((q for q in db["quizzes"] if q["id"] == quiz_id), None)
        if not qz:
            return None
        qs = sorted(
            [qq for qq in db["quiz_questions"] if qq["quiz_id"] == quiz_id],
            key=lambda x: x.get("order_index", 0),
        )
        return {**qz, "questions": qs}

    def save_quiz_attempt(self, attempt_data: dict[str, Any]) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "attempted_at": self._now_iso(),
            **attempt_data,
        }
        if self._client:
            res = self._client.table("quiz_attempts").insert(record).execute()
            return res.data[0]
        db = self._load_local_db()
        db["quiz_attempts"].insert(0, record)
        self._save_local_db(db)
        return record

    # ---------------- Flashcards ----------------
    def create_flashcards(self, doc_id: str, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = self._now_iso()
        records = [
            {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "mastery_level": "again",
                "next_review_at": now,
                "created_at": now,
                **c,
            }
            for c in cards
        ]
        if self._client:
            res = self._client.table("flashcards").insert(records).execute()
            return res.data
        db = self._load_local_db()
        db["flashcards"] = records + db["flashcards"]
        self._save_local_db(db)
        return records

    def list_flashcards(self, doc_id: str) -> list[dict[str, Any]]:
        if self._client:
            return (
                self._client.table("flashcards")
                .select("*")
                .eq("document_id", doc_id)
                .order("created_at", desc=True)
                .execute()
                .data
            )
        db = self._load_local_db()
        return [fc for fc in db["flashcards"] if fc["document_id"] == doc_id]

    def update_flashcard_mastery(self, card_id: str, mastery_level: str) -> Optional[dict[str, Any]]:
        days_map = {"again": 0, "hard": 1, "good": 3, "easy": 7}
        next_review = (datetime.now(timezone.utc) + timedelta(days=days_map.get(mastery_level, 1))).isoformat()
        if self._client:
            res = (
                self._client.table("flashcards")
                .update({"mastery_level": mastery_level, "next_review_at": next_review})
                .eq("id", card_id)
                .execute()
            )
            return res.data[0] if res.data else None
        db = self._load_local_db()
        for fc in db["flashcards"]:
            if fc["id"] == card_id:
                fc["mastery_level"] = mastery_level
                fc["next_review_at"] = next_review
                self._save_local_db(db)
                return fc
        return None

    # ---------------- Feynman Sessions ----------------
    def save_feynman_session(self, doc_id: str, topic: str, user_explanation: str, ai_feedback: dict) -> dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "topic": topic,
            "user_explanation": user_explanation,
            "ai_feedback": ai_feedback,
            "created_at": self._now_iso(),
        }
        if self._client:
            res = self._client.table("feynman_sessions").insert(record).execute()
            return res.data[0]
        db = self._load_local_db()
        db["feynman_sessions"].insert(0, record)
        self._save_local_db(db)
        return record

    def list_feynman_sessions(self, doc_id: str) -> list[dict[str, Any]]:
        if self._client:
            return (
                self._client.table("feynman_sessions")
                .select("*")
                .eq("document_id", doc_id)
                .order("created_at", desc=True)
                .execute()
                .data
            )
        db = self._load_local_db()
        return [fs for fs in db["feynman_sessions"] if fs["document_id"] == doc_id]

    # ---------------- History ----------------
    def get_full_history(self) -> dict[str, Any]:
        if self._client:
            docs = self.list_documents()
            attempts = self._client.table("quiz_attempts").select("*").order("attempted_at", desc=True).limit(50).execute().data
            quizzes = self._client.table("quizzes").select("*").execute().data
            questions = self._client.table("quiz_questions").select("*").execute().data
            review_cards = self._client.table("flashcards").select("*").in_("mastery_level", ["again", "hard"]).execute().data
            feynman = self._client.table("feynman_sessions").select("*").order("created_at", desc=True).limit(20).execute().data
        else:
            db = self._load_local_db()
            docs = [{k: v for k, v in d.items() if k != "page_contents"} for d in db["documents"]]
            attempts = db["quiz_attempts"][:50]
            quizzes = db["quizzes"]
            questions = db["quiz_questions"]
            review_cards = [fc for fc in db["flashcards"] if fc.get("mastery_level") in ("again", "hard")]
            feynman = db["feynman_sessions"][:20]

        doc_map = {d["id"]: d for d in docs}
        quiz_map = {q["id"]: q for q in quizzes}
        question_map = {qq["id"]: qq for qq in questions}

        enriched_attempts = []
        wrong_questions = []
        seen_wrong_ids = set()

        for att in attempts:
            qz = quiz_map.get(att["quiz_id"], {})
            doc = doc_map.get(qz.get("document_id"), {})
            enriched_attempts.append({
                **att,
                "quiz_title": qz.get("title", "삭제된 퀴즈"),
                "difficulty": qz.get("difficulty", ""),
                "document_id": qz.get("document_id", ""),
                "document_title": doc.get("title", "삭제된 자료"),
                "category": doc.get("category", ""),
            })
            for ans in att.get("user_answers", []):
                if not ans.get("is_correct") and ans.get("question_id") not in seen_wrong_ids:
                    q_obj = question_map.get(ans.get("question_id"))
                    if q_obj:
                        seen_wrong_ids.add(q_obj["id"])
                        wrong_questions.append({
                            **q_obj,
                            "document_id": qz.get("document_id", ""),
                            "document_title": doc.get("title", ""),
                            "last_user_answer": ans.get("user_answer", ""),
                        })

        return {
            "documents_count": len(docs),
            "attempts": enriched_attempts,
            "wrong_questions": wrong_questions,
            "review_flashcards": review_cards,
            "feynman_sessions": feynman,
        }


store = DataStoreService()

