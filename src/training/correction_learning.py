import hashlib
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_confidence(value: Any) -> float:
    confidence = _safe_float(value, 0.0)
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return round(confidence, 4)


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    
    text = text.replace("\x00", " ")
    return text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    return " ".join(_clean_text(value).strip().lower().split())


def _guess_field(value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return "unknown"
    return normalized


@dataclass
class CorrectionSample:
    sample_id: str
    resume_id: int
    field_name: str
    original_value: str
    corrected_value: str
    confidence_before: float
    confidence_after: float
    feedback_type: str
    status: str
    source: str
    user_id: Optional[str]
    session_id: Optional[str]
    comment: str
    model_name: str
    model_version: str
    extraction_context: Dict[str, Any]
    timestamp: str


class CorrectionLearningStore:
    DEFAULT_SAMPLES_FILE = "structured_corrections.jsonl"
    DEFAULT_REPORT_FILE = "error_analysis.json"
    DEFAULT_STATE_FILE = "retrain_state.json"

    def __init__(
        self,
        samples_path: Optional[str] = None,
        report_path: Optional[str] = None,
        state_path: Optional[str] = None,
    ):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        learning_dir = os.path.join(base_dir, "learning_data")
        os.makedirs(learning_dir, exist_ok=True)

        self.samples_path = samples_path or os.path.join(learning_dir, self.DEFAULT_SAMPLES_FILE)
        self.report_path = report_path or os.path.join(learning_dir, self.DEFAULT_REPORT_FILE)
        self.state_path = state_path or os.path.join(learning_dir, self.DEFAULT_STATE_FILE)

        self._ensure_files()

    def _ensure_files(self) -> None:
        os.makedirs(os.path.dirname(self.samples_path), exist_ok=True)
        if not os.path.exists(self.samples_path):
            with open(self.samples_path, "w", encoding="utf-8") as f:
                f.write("")

        if not os.path.exists(self.report_path):
            self.save_report(
                {
                    "generated_at": _utcnow_iso(),
                    "summary": {},
                    "fields": {},
                }
            )

        if not os.path.exists(self.state_path):
            self.save_state(
                {
                    "last_run_at": None,
                    "last_approved_sample_count": 0,
                    "last_registry_version": None,
                    "last_deployed": False,
                }
            )

    def add_sample(
        self,
        *,
        resume_id: Optional[int],
        field_name: str,
        original_value: str,
        corrected_value: str,
        confidence_before: float = 0.0,
        confidence_after: Optional[float] = None,
        feedback_type: str = "correction",
        status: str = "approved",
        source: str = "ui",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        comment: str = "",
        model_name: str = "",
        model_version: str = "",
        extraction_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        field = _guess_field(_clean_text(field_name))
        original = _clean_text(original_value)
        corrected = _clean_text(corrected_value)
        confidence_before = _clamp_confidence(confidence_before)
        if confidence_after is None:
            confidence_after = 1.0 if normalize_text(original) != normalize_text(corrected) and corrected else confidence_before
        confidence_after = _clamp_confidence(confidence_after)

        timestamp = _utcnow_iso()
        digest = hashlib.md5(
            f"{timestamp}|{field}|{original}|{corrected}".encode("utf-8", errors="replace")
        ).hexdigest()[:8]
        sample_id = f"cs_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{digest}"

        sample = CorrectionSample(
            sample_id=sample_id,
            resume_id=int(resume_id or 0),
            field_name=field,
            original_value=original,
            corrected_value=corrected,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            feedback_type=str(feedback_type or "correction"),
            status=str(status or "approved"),
            source=str(source or "ui"),
            user_id=user_id,
            session_id=session_id,
            comment=_clean_text(comment),
            model_name=_clean_text(model_name),
            model_version=_clean_text(model_version),
            extraction_context=extraction_context or {},
            timestamp=timestamp,
        )

        record = sample.__dict__
        with open(self.samples_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        logger.info("Structured correction sample stored: %s (%s)", sample_id, field)
        return record

    def add_samples(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        stored: List[Dict[str, Any]] = []
        for sample in samples:
            stored.append(
                self.add_sample(
                    resume_id=sample.get("resume_id"),
                    field_name=sample.get("field_name", ""),
                    original_value=sample.get("original_value", ""),
                    corrected_value=sample.get("corrected_value", ""),
                    confidence_before=sample.get("confidence_before", 0.0),
                    confidence_after=sample.get("confidence_after"),
                    feedback_type=sample.get("feedback_type", "correction"),
                    status=sample.get("status", "approved"),
                    source=sample.get("source", "ui"),
                    user_id=sample.get("user_id"),
                    session_id=sample.get("session_id"),
                    comment=sample.get("comment", ""),
                    model_name=sample.get("model_name", ""),
                    model_version=sample.get("model_version", ""),
                    extraction_context=sample.get("extraction_context", {}),
                )
            )
        return stored

    def load_samples(
        self,
        *,
        field_name: Optional[str] = None,
        status: Optional[str] = None,
        feedback_type: Optional[str] = None,
        only_changed: bool = False,
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(self.samples_path):
            return []

        target_field = _guess_field(field_name) if field_name else None
        samples: List[Dict[str, Any]] = []

        with open(self.samples_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if target_field and _guess_field(sample.get("field_name", "")) != target_field:
                    continue
                if status and sample.get("status") != status:
                    continue
                if feedback_type and sample.get("feedback_type") != feedback_type:
                    continue
                if only_changed:
                    if normalize_text(sample.get("original_value", "")) == normalize_text(sample.get("corrected_value", "")):
                        continue
                samples.append(sample)

        return samples

    def update_sample_status(self, sample_id: str, status: str) -> bool:
        if not sample_id or not os.path.exists(self.samples_path):
            return False

        target_status = str(status or "").strip().lower()
        if target_status not in {"pending", "approved", "rejected"}:
            return False

        updated = False
        rewritten: List[str] = []

        with open(self.samples_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                except json.JSONDecodeError:
                    continue

                context = sample.get("extraction_context") or {}
                context_feedback_id = context.get("feedback_id")
                context_correction_id = context.get("correction_id")

                if (
                    sample.get("sample_id") == sample_id
                    or context_feedback_id == sample_id
                    or context_correction_id == sample_id
                ):
                    sample["status"] = target_status
                    sample["updated_at"] = _utcnow_iso()
                    updated = True

                rewritten.append(json.dumps(sample, ensure_ascii=True))

        if updated:
            with open(self.samples_path, "w", encoding="utf-8") as f:
                for line in rewritten:
                    f.write(line + "\n")

        return updated

    def get_statistics(self) -> Dict[str, Any]:
        samples = self.load_samples()
        stats = {
            "total_samples": len(samples),
            "approved_samples": 0,
            "pending_samples": 0,
            "rejected_samples": 0,
            "changed_samples": 0,
            "by_field": {},
            "by_feedback_type": {},
            "storage_path": self.samples_path,
        }

        for sample in samples:
            status = sample.get("status", "approved")
            feedback_type = sample.get("feedback_type", "correction")
            field = _guess_field(sample.get("field_name", ""))

            if status == "approved":
                stats["approved_samples"] += 1
            elif status == "pending":
                stats["pending_samples"] += 1
            elif status == "rejected":
                stats["rejected_samples"] += 1

            if normalize_text(sample.get("original_value", "")) != normalize_text(sample.get("corrected_value", "")):
                stats["changed_samples"] += 1

            stats["by_feedback_type"][feedback_type] = stats["by_feedback_type"].get(feedback_type, 0) + 1
            stats["by_field"][field] = stats["by_field"].get(field, 0) + 1

        return stats

    def count_samples(self, *, status: Optional[str] = None, only_changed: bool = False) -> int:
        return len(self.load_samples(status=status, only_changed=only_changed))

    def save_report(self, report: Dict[str, Any]) -> None:
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=True)

    def load_report(self) -> Dict[str, Any]:
        if not os.path.exists(self.report_path):
            return {}
        try:
            with open(self.report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=True)

    def load_state(self) -> Dict[str, Any]:
        if not os.path.exists(self.state_path):
            return {}
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}


class CorrectionPatternMiner:
    def __init__(self, store: Optional[CorrectionLearningStore] = None):
        self.store = store or get_correction_learning_store()

    def analyze(
        self,
        *,
        samples: Optional[List[Dict[str, Any]]] = None,
        low_confidence_threshold: float = 0.65,
        top_pairs: int = 10,
    ) -> Dict[str, Any]:
        rows = samples if samples is not None else self.store.load_samples(status="approved")
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for sample in rows:
            grouped[_guess_field(sample.get("field_name", ""))].append(sample)

        analysis = {
            "generated_at": _utcnow_iso(),
            "summary": {
                "total_samples": len(rows),
                "field_count": len(grouped),
                "low_confidence_threshold": low_confidence_threshold,
            },
            "fields": {},
            "top_problem_fields": [],
        }

        field_rank: List[Tuple[str, float]] = []

        for field, samples_for_field in grouped.items():
            total = len(samples_for_field)
            changed = 0
            low_confidence = 0
            low_confidence_changed = 0
            confidence_sum = 0.0

            pair_data: Dict[Tuple[str, str], Dict[str, Any]] = {}

            for sample in samples_for_field:
                before = _clamp_confidence(sample.get("confidence_before", 0.0))
                confidence_sum += before

                original = str(sample.get("original_value", ""))
                corrected = str(sample.get("corrected_value", ""))
                original_norm = normalize_text(original)
                corrected_norm = normalize_text(corrected)

                is_changed = bool(corrected_norm) and original_norm != corrected_norm
                if is_changed:
                    changed += 1

                if before < low_confidence_threshold:
                    low_confidence += 1
                    if is_changed:
                        low_confidence_changed += 1

                if not is_changed:
                    continue

                key = (original_norm, corrected.strip())
                if key not in pair_data:
                    pair_data[key] = {
                        "original_example": original.strip(),
                        "corrected": corrected.strip(),
                        "original_normalized": original_norm,
                        "count": 0,
                        "confidence_sum": 0.0,
                    }

                pair_data[key]["count"] += 1
                pair_data[key]["confidence_sum"] += before

            common_mistakes = []
            for pair in pair_data.values():
                count = pair["count"]
                avg_before = pair["confidence_sum"] / count if count else 0.0
                common_mistakes.append(
                    {
                        "original": pair["original_example"],
                        "corrected": pair["corrected"],
                        "original_normalized": pair["original_normalized"],
                        "count": count,
                        "avg_confidence_before": round(avg_before, 4),
                    }
                )

            common_mistakes.sort(key=lambda x: (-x["count"], x["avg_confidence_before"]))
            common_mistakes = common_mistakes[:top_pairs]

            avg_confidence = round(confidence_sum / total, 4) if total else 0.0
            error_rate = round(changed / total, 4) if total else 0.0
            low_confidence_error_rate = (
                round(low_confidence_changed / low_confidence, 4) if low_confidence else 0.0
            )

            severity = (error_rate * 0.6 + low_confidence_error_rate * 0.4) * max(1.0, total / 5.0)
            field_rank.append((field, severity))

            analysis["fields"][field] = {
                "total_samples": total,
                "changed_samples": changed,
                "error_rate": error_rate,
                "avg_confidence_before": avg_confidence,
                "low_confidence_samples": low_confidence,
                "low_confidence_error_rate": low_confidence_error_rate,
                "common_mistakes": common_mistakes,
            }

        field_rank.sort(key=lambda item: item[1], reverse=True)
        analysis["top_problem_fields"] = [field for field, _ in field_rank[:5]]
        return analysis

    def run_and_store(
        self,
        *,
        low_confidence_threshold: float = 0.65,
        top_pairs: int = 10,
    ) -> Dict[str, Any]:
        report = self.analyze(
            low_confidence_threshold=low_confidence_threshold,
            top_pairs=top_pairs,
        )
        self.store.save_report(report)
        return report


class CorrectionModelTrainer:
    MODEL_NAME = "correction_postprocessor"

    def __init__(
        self,
        store: Optional[CorrectionLearningStore] = None,
        miner: Optional[CorrectionPatternMiner] = None,
        models_dir: Optional[str] = None,
    ):
        self.store = store or get_correction_learning_store()
        self.miner = miner or CorrectionPatternMiner(self.store)

        if models_dir is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            models_dir = os.path.join(base_dir, "models", self.MODEL_NAME)

        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)

    def train_and_register(
        self,
        *,
        min_samples: int = 1,
        min_rule_support: int = 1,
        low_confidence_threshold: float = 0.65,
        min_similarity: float = 0.9,
        deploy: bool = True,
    ) -> Dict[str, Any]:
        approved_changed = self.store.load_samples(status="approved", only_changed=True)
        if len(approved_changed) < min_samples:
            return {
                "success": False,
                "message": f"Insufficient approved changed samples ({len(approved_changed)} < {min_samples})",
                "sample_count": len(approved_changed),
            }

        report = self.miner.analyze(
            samples=approved_changed,
            low_confidence_threshold=low_confidence_threshold,
        )

        fields: Dict[str, Dict[str, Any]] = {}
        total_rules = 0

        for field, field_stats in report.get("fields", {}).items():
            exact_map: Dict[str, str] = {}
            fuzzy_pairs: List[Dict[str, Any]] = []

            for pair in field_stats.get("common_mistakes", []):
                if pair.get("count", 0) < min_rule_support:
                    continue

                original_norm = normalize_text(pair.get("original_normalized", ""))
                corrected_value = str(pair.get("corrected", "")).strip()
                if not original_norm or not corrected_value:
                    continue

                if original_norm not in exact_map:
                    exact_map[original_norm] = corrected_value

                fuzzy_pairs.append(
                    {
                        "original_normalized": original_norm,
                        "corrected_value": corrected_value,
                        "count": int(pair.get("count", 0)),
                        "avg_confidence_before": _safe_float(pair.get("avg_confidence_before", 0.0)),
                    }
                )

            if exact_map or fuzzy_pairs:
                fields[field] = {
                    "exact_map": exact_map,
                    "fuzzy_pairs": fuzzy_pairs,
                }
                total_rules += len(exact_map)

        if not fields:
            return {
                "success": False,
                "message": "No rules could be generated from current samples",
                "sample_count": len(approved_changed),
            }

        model_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        digest = hashlib.md5(f"{model_stamp}|{total_rules}".encode("utf-8")).hexdigest()[:6]
        model_dir = os.path.join(self.models_dir, f"model_{model_stamp}_{digest}")
        os.makedirs(model_dir, exist_ok=True)

        artifact = {
            "model_name": self.MODEL_NAME,
            "created_at": _utcnow_iso(),
            "sample_count": len(approved_changed),
            "rule_count": total_rules,
            "low_confidence_threshold": low_confidence_threshold,
            "min_similarity": min_similarity,
            "fields": fields,
            "analysis": report,
        }

        artifact_path = os.path.join(model_dir, "artifact.json")
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, indent=2, ensure_ascii=True)

        from src.training.model_registry import get_model_registry

        registry = get_model_registry()
        registry_version = registry.register_model(
            model_name=self.MODEL_NAME,
            model_path=model_dir,
            model_type="correction-rules",
            config={
                "min_samples": min_samples,
                "min_rule_support": min_rule_support,
                "low_confidence_threshold": low_confidence_threshold,
                "min_similarity": min_similarity,
            },
            metrics={
                "sample_count": float(len(approved_changed)),
                "rule_count": float(total_rules),
            },
            description="Pattern-mined correction postprocessor model",
        )

        deployed = False
        if deploy:
            deployed = registry.deploy_version(self.MODEL_NAME, registry_version)

        return {
            "success": True,
            "message": "Correction model trained",
            "model_path": model_dir,
            "artifact_path": artifact_path,
            "registry_version": registry_version,
            "deployed": deployed,
            "sample_count": len(approved_changed),
            "rule_count": total_rules,
            "fields": list(fields.keys()),
        }


class CorrectionModelEngine:
    MODEL_NAME = "correction_postprocessor"
    DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.65
    DEFAULT_MIN_SIMILARITY = 0.9
    MIN_SAMPLES_TO_APPLY = 1  
    MIN_RULES_TO_APPLY = 1  

    def __init__(self):
        self._cached_version_id: Optional[str] = None
        self._cached_artifact: Optional[Dict[str, Any]] = None
        self._cached_live_mtime: Optional[float] = None
        self._cached_live_map: Optional[Dict[str, Dict[str, str]]] = None

    def _load_live_exact_map(self) -> Dict[str, Dict[str, str]]:
        try:
            store = get_correction_learning_store()
            if not os.path.exists(store.samples_path):
                self._cached_live_mtime = None
                self._cached_live_map = {}
                return {}

            mtime = os.path.getmtime(store.samples_path)
            if (
                self._cached_live_map is not None
                and self._cached_live_mtime is not None
                and self._cached_live_mtime == mtime
            ):
                return self._cached_live_map

            rows = store.load_samples()
            rows.sort(key=lambda sample: str(sample.get("timestamp", "")))

            live_map: Dict[str, Dict[str, str]] = {}
            for sample in rows:
                field = _guess_field(sample.get("field_name", ""))
                original_norm = normalize_text(sample.get("original_value", ""))
                corrected = str(sample.get("corrected_value", "")).strip()
                corrected_norm = normalize_text(corrected)
                feedback_type = str(sample.get("feedback_type", "correction")).strip().lower()
                status = str(sample.get("status", "approved")).strip().lower()

                if not original_norm:
                    continue

                
                is_delete = (
                    status == "rejected"
                    or feedback_type == "rejection"
                    or (feedback_type == "correction" and not corrected_norm)
                )
                if is_delete:
                    existing = live_map.get(field)
                    if existing and original_norm in existing:
                        del existing[original_norm]
                    continue

                if status != "approved":
                    continue

                if feedback_type != "correction":
                    continue

                if not corrected_norm or corrected_norm == original_norm:
                    continue

                live_map.setdefault(field, {})[original_norm] = corrected

            self._cached_live_mtime = mtime
            self._cached_live_map = live_map
            return live_map
        except Exception as e:
            logger.debug("Could not load live correction map: %s", e)
            return {}

    def _load_artifact(self) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            from src.training.model_registry import get_model_registry

            registry = get_model_registry()
            version = registry.get_active_version(self.MODEL_NAME)
            if version is None:
                version = registry.get_latest_version(self.MODEL_NAME)
            if version is None:
                return None, None

            if version.version_id == self._cached_version_id and self._cached_artifact is not None:
                return self._cached_artifact, self._cached_version_id

            
            artifact_path = None
            
            
            if os.path.exists(os.path.join(version.path, "artifact.json")):
                artifact_path = os.path.join(version.path, "artifact.json")
            
            
            if artifact_path is None:
                base_dir = os.path.dirname(os.path.dirname(__file__))
                local_models_dir = os.path.join(base_dir, "models", "correction_postprocessor")
                if os.path.exists(local_models_dir):
                    for folder in os.listdir(local_models_dir):
                        candidate = os.path.join(local_models_dir, folder, "artifact.json")
                        if os.path.exists(candidate):
                            artifact_path = candidate
                            break
            
            
            if artifact_path is None:
                try:
                    
                    version_folder = os.path.basename(version.path)
                    if version_folder.startswith("model_"):
                        base_dir = os.path.dirname(os.path.dirname(__file__))
                        candidate = os.path.join(base_dir, "models", "correction_postprocessor", version_folder, "artifact.json")
                        if os.path.exists(candidate):
                            artifact_path = candidate
                except:
                    pass
            
            if artifact_path is None:
                logger.debug("Could not find artifact.json in any location")
                return None, None

            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)

            self._cached_version_id = version.version_id
            self._cached_artifact = artifact
            return artifact, version.version_id
        except Exception as e:
            logger.debug("Could not load correction model artifact: %s", e)
            return None, None

    def get_model_status(self) -> Dict[str, Any]:
        artifact, version = self._load_artifact()
        if artifact is None:
            return {"available": False}
        sample_count = int(artifact.get("sample_count", 0) or 0)
        rule_count = int(artifact.get("rule_count", 0) or 0)
        return {
            "available": True,
            "version": version,
            "created_at": artifact.get("created_at"),
            "sample_count": sample_count,
            "rule_count": rule_count,
            "field_count": len(artifact.get("fields", {})),
            "can_auto_apply": sample_count >= self.MIN_SAMPLES_TO_APPLY and rule_count >= self.MIN_RULES_TO_APPLY,
            "min_samples_to_apply": self.MIN_SAMPLES_TO_APPLY,
            "min_rules_to_apply": self.MIN_RULES_TO_APPLY,
        }

    def apply(
        self,
        *,
        field_name: str,
        value: str,
        confidence: float = 0.0,
        force: bool = False,
    ) -> Dict[str, Any]:
        if value is None:
            return {
                "applied": False,
                "corrected_value": value,
                "confidence": _clamp_confidence(confidence),
                "reason": None,
                "similarity": None,
                "model_version": None,
            }

        original_value = str(value)
        original_norm = normalize_text(original_value)
        current_confidence = _clamp_confidence(confidence)
        field = _guess_field(field_name)

        
        live_map = self._load_live_exact_map()
        live_field = live_map.get(field, {})
        if original_norm and original_norm in live_field:
            corrected = live_field[original_norm]
            if normalize_text(corrected) != original_norm:
                return {
                    "applied": True,
                    "corrected_value": corrected,
                    "confidence": max(current_confidence, 0.98),
                    "reason": "live_feedback_exact",
                    "similarity": 1.0,
                    "model_version": "live-feedback",
                }

        artifact, version_id = self._load_artifact()
        if artifact is None:
            return {
                "applied": False,
                "corrected_value": original_value,
                "confidence": current_confidence,
                "reason": None,
                "similarity": None,
                "model_version": None,
            }

        sample_count = int(artifact.get("sample_count", 0) or 0)
        rule_count = int(artifact.get("rule_count", 0) or 0)
        if not force and (
            sample_count < self.MIN_SAMPLES_TO_APPLY
            or rule_count < self.MIN_RULES_TO_APPLY
        ):
            return {
                "applied": False,
                "corrected_value": original_value,
                "confidence": current_confidence,
                "reason": "model_not_mature",
                "similarity": None,
                "model_version": version_id,
            }

        field_rules = artifact.get("fields", {}).get(field, {})
        exact_map = field_rules.get("exact_map", {})

        if original_norm in exact_map:
            corrected = exact_map[original_norm]
            if normalize_text(corrected) != original_norm:
                return {
                    "applied": True,
                    "corrected_value": corrected,
                    "confidence": max(current_confidence, 0.95),
                    "reason": "exact_match",
                    "similarity": 1.0,
                    "model_version": version_id,
                }

        low_confidence_threshold = _safe_float(
            artifact.get("low_confidence_threshold", self.DEFAULT_LOW_CONFIDENCE_THRESHOLD),
            self.DEFAULT_LOW_CONFIDENCE_THRESHOLD,
        )
        min_similarity = _safe_float(
            artifact.get("min_similarity", self.DEFAULT_MIN_SIMILARITY),
            self.DEFAULT_MIN_SIMILARITY,
        )

        if current_confidence > low_confidence_threshold and not force:
            return {
                "applied": False,
                "corrected_value": original_value,
                "confidence": current_confidence,
                "reason": None,
                "similarity": None,
                "model_version": version_id,
            }

        best_match: Optional[Dict[str, Any]] = None
        for candidate in field_rules.get("fuzzy_pairs", []):
            candidate_original = normalize_text(candidate.get("original_normalized", ""))
            if not candidate_original:
                continue

            similarity = SequenceMatcher(None, original_norm, candidate_original).ratio()
            if similarity < min_similarity:
                continue

            candidate_count = int(candidate.get("count", 0))
            if best_match is None:
                best_match = {
                    "similarity": similarity,
                    "count": candidate_count,
                    "corrected_value": candidate.get("corrected_value", ""),
                }
                continue

            if similarity > best_match["similarity"]:
                best_match = {
                    "similarity": similarity,
                    "count": candidate_count,
                    "corrected_value": candidate.get("corrected_value", ""),
                }
            elif similarity == best_match["similarity"] and candidate_count > best_match["count"]:
                best_match = {
                    "similarity": similarity,
                    "count": candidate_count,
                    "corrected_value": candidate.get("corrected_value", ""),
                }

        if best_match:
            corrected_value = str(best_match["corrected_value"] or "").strip()
            if corrected_value and normalize_text(corrected_value) != original_norm:
                boosted = max(current_confidence, min(0.93, 0.62 + 0.38 * best_match["similarity"]))
                return {
                    "applied": True,
                    "corrected_value": corrected_value,
                    "confidence": round(boosted, 4),
                    "reason": "fuzzy_match",
                    "similarity": round(best_match["similarity"], 4),
                    "model_version": version_id,
                }

        return {
            "applied": False,
            "corrected_value": original_value,
            "confidence": current_confidence,
            "reason": None,
            "similarity": None,
            "model_version": version_id,
        }


class AutoRetrainer:
    def __init__(
        self,
        store: Optional[CorrectionLearningStore] = None,
        trainer: Optional[CorrectionModelTrainer] = None,
        *,
        min_new_samples: int = 1,
        min_hours_between_runs: int = 0,
        min_samples_to_train: int = 1,
        min_rule_support: int = 1,
        auto_deploy: bool = True,
    ):
        self.store = store or get_correction_learning_store()
        self.trainer = trainer or CorrectionModelTrainer(self.store)
        self.min_new_samples = int(min_new_samples)
        self.min_hours_between_runs = int(min_hours_between_runs)
        self.min_samples_to_train = int(min_samples_to_train)
        self.min_rule_support = int(min_rule_support)
        self.auto_deploy = bool(auto_deploy)

    def _hours_since_last_run(self) -> Optional[float]:
        state = self.store.load_state()
        last_run_at = state.get("last_run_at")
        if not last_run_at:
            return None
        try:
            last_dt = datetime.fromisoformat(last_run_at)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_dt
            return delta.total_seconds() / 3600.0
        except (TypeError, ValueError):
            return None

    def status(self) -> Dict[str, Any]:
        state = self.store.load_state()
        approved_changed = self.store.count_samples(status="approved", only_changed=True)
        last_count = int(state.get("last_approved_sample_count", 0) or 0)
        new_since_last = max(0, approved_changed - last_count)
        hours_since = self._hours_since_last_run()

        enough_time = hours_since is None or hours_since >= self.min_hours_between_runs
        enough_new_samples = new_since_last >= self.min_new_samples
        enough_total_samples = approved_changed >= self.min_samples_to_train

        ready = enough_time and enough_new_samples and enough_total_samples
        return {
            "ready": ready,
            "approved_changed_samples": approved_changed,
            "new_samples_since_last_run": new_since_last,
            "last_run_at": state.get("last_run_at"),
            "last_registry_version": state.get("last_registry_version"),
            "hours_since_last_run": round(hours_since, 4) if hours_since is not None else None,
            "conditions": {
                "enough_time": enough_time,
                "enough_new_samples": enough_new_samples,
                "enough_total_samples": enough_total_samples,
            },
            "thresholds": {
                "min_new_samples": self.min_new_samples,
                "min_hours_between_runs": self.min_hours_between_runs,
                "min_samples_to_train": self.min_samples_to_train,
            },
        }

    def maybe_retrain(self, *, force: bool = False, deploy: Optional[bool] = None) -> Dict[str, Any]:
        current_status = self.status()
        if not force and not current_status.get("ready"):
            return {
                "triggered": False,
                "reason": "conditions_not_met",
                "status": current_status,
            }

        do_deploy = self.auto_deploy if deploy is None else bool(deploy)
        result = self.trainer.train_and_register(
            min_samples=self.min_samples_to_train,
            min_rule_support=self.min_rule_support,
            deploy=do_deploy,
        )

        if result.get("success"):
            state = self.store.load_state()
            state["last_run_at"] = _utcnow_iso()
            state["last_approved_sample_count"] = self.store.count_samples(
                status="approved",
                only_changed=True,
            )
            state["last_registry_version"] = result.get("registry_version")
            state["last_deployed"] = bool(result.get("deployed"))
            self.store.save_state(state)

        return {
            "triggered": True,
            "forced": force,
            "result": result,
            "status": self.status(),
        }


_correction_learning_store: Optional[CorrectionLearningStore] = None
_correction_pattern_miner: Optional[CorrectionPatternMiner] = None
_correction_model_trainer: Optional[CorrectionModelTrainer] = None
_correction_model_engine: Optional[CorrectionModelEngine] = None
_auto_retrainer: Optional[AutoRetrainer] = None


def get_correction_learning_store() -> CorrectionLearningStore:
    global _correction_learning_store
    if _correction_learning_store is None:
        _correction_learning_store = CorrectionLearningStore()
    return _correction_learning_store


def get_correction_pattern_miner() -> CorrectionPatternMiner:
    global _correction_pattern_miner
    if _correction_pattern_miner is None:
        _correction_pattern_miner = CorrectionPatternMiner(get_correction_learning_store())
    return _correction_pattern_miner


def get_correction_model_trainer() -> CorrectionModelTrainer:
    global _correction_model_trainer
    if _correction_model_trainer is None:
        _correction_model_trainer = CorrectionModelTrainer(
            get_correction_learning_store(),
            get_correction_pattern_miner(),
        )
    return _correction_model_trainer


def get_correction_model_engine() -> CorrectionModelEngine:
    global _correction_model_engine
    if _correction_model_engine is None:
        _correction_model_engine = CorrectionModelEngine()
    return _correction_model_engine


def get_auto_retrainer() -> AutoRetrainer:
    global _auto_retrainer
    if _auto_retrainer is None:
        _auto_retrainer = AutoRetrainer(
            get_correction_learning_store(),
            get_correction_model_trainer(),
        )
    return _auto_retrainer
