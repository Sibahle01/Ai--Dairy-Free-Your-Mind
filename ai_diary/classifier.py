# classifier.py
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@dataclass
class ClassificationResult:
    entry: str
    main_category: str
    secondary_category: Optional[str] = None
    sub_category: Optional[str] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    sub_confidence: Optional[float] = None
    processing_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Return a dictionary representation of the classification result."""
        return {
            "entry": self.entry,
            "main_category": self.main_category,
            "secondary_category": self.secondary_category,
            "sub_category": self.sub_category,
            "confidence_scores": self.confidence_scores,
            "sub_confidence": self.sub_confidence,
            "processing_time": self.processing_time,
            "success": self.success,
            "error_message": self.error_message
        }

class RobustJournalClassifier:
    def __init__(self, min_secondary_confidence=0.25, min_sub_confidence=0.35, max_entry_length=5000):
        self.min_secondary_confidence = min_secondary_confidence
        self.min_sub_confidence = min_sub_confidence
        self.max_entry_length = max_entry_length
        self._pipe = None

        self.category_desc = {
            "Reflection": "A personal reflection, insight, lesson learned, or thoughtful observation about life experiences",
            "Goals": "A goal, aspiration, desired achievement, or future ambition including career, personal, or financial objectives",
            "Emotions": "An emotional state, feeling, mood, or expression (e.g., happiness, sadness, anger, anxiety)",
            "Plans": "A concrete plan, task, intention, decision, or specific action item for the near or distant future",
            "Relationships": "Thoughts or experiences about family, friends, romantic partners, or social connections",
            "Challenges": "A problem, difficulty, obstacle, or struggle being faced or overcome",
            "Gratitude": "Thankfulness, appreciation, or recognition of positive things in life",
            "Health": "Physical health, mental wellness, fitness, medical concerns, or self-care activities",
            "Habits": "Daily or weekly routines, consistency, discipline, breaking or building habits",
        }

        self.sub_map = {
            "Emotions": ["Anxiety","Sadness","Anger","Frustration","Stress","Loneliness","Joy","Calm","Contentment","Grief"],
            "Goals": ["Savings/Finance","Career/Skill","Education/Learning","Health/Fitness","Habit Building","Relationship","Home/Organizing","Travel","Creative/Art"],
            "Plans": ["Work/Tasks","Errands","Appointments","Study Plan","Fitness Plan","Meal Prep","Travel Plan"],
            "Health": ["Exercise","Sleep","Nutrition","Mental Health","Medical Checkup","Medication","Therapy"],
            "Relationships": ["Family","Romantic","Friends","Colleagues","Conflict","Support"],
            "Challenges": ["Time Management","Financial Pressure","Workload","Motivation","Procrastination","Imposter Syndrome"],
            "Gratitude": ["People","Work","Nature","Health","Small Joys"],
            "Habits": ["Phone/Screen Time","Discipline","Routine","Focus","Consistency"],
            "Reflection": ["Self-Awareness","Lesson Learned","Perspective Shift","Acceptance"]
        }

    @lru_cache(maxsize=1)
    def _get_pipe(self):
        from transformers import pipeline
        try:
            import torch
            device = 0 if torch.cuda.is_available() else -1
        except Exception:
            device = -1
        logger.info("Loading zero-shot model…")
        return pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=device, return_all_scores=True)

    def _validate(self, entry: str) -> Tuple[bool, Optional[str]]:
        if not isinstance(entry, str) or not entry.strip():
            return False, "Entry cannot be empty"
        if len(entry) > self.max_entry_length:
            return False, f"Entry too long (>{self.max_entry_length} chars)"
        return True, None

    def classify_single(self, entry: str) -> ClassificationResult:
        t0 = time.time()
        ok, msg = self._validate(entry)
        if not ok:
            return ClassificationResult(entry=entry, main_category="Unknown", secondary_category=None, success=False, error_message=msg)

        try:
            pipe = self._get_pipe()
            cand = list(self.category_desc.values())
            out = pipe(entry.strip(), candidate_labels=cand)

            labels = out["labels"]
            scores = out["scores"]
            top2 = list(zip(labels[:2], scores[:2]))

            def to_short(desc: str) -> str:
                for k, v in self.category_desc.items():
                    if v == desc:
                        return k
                return "Unknown"

            mapped = [(to_short(d), float(s)) for d, s in top2]
            main_category = mapped[0][0]
            secondary_category = mapped[1][0] if len(mapped) > 1 and mapped[1][1] >= self.min_secondary_confidence else None
            confidence_scores = {mc[0]: round(mc[1], 3) for mc in mapped}

            # Subcategory
            sub_label, sub_conf = None, None
            if main_category in self.sub_map:
                sub_out = pipe(entry.strip(), candidate_labels=self.sub_map[main_category])
                sub_label = sub_out["labels"][0]
                sub_conf = float(sub_out["scores"][0])
                if sub_conf < self.min_sub_confidence:
                    sub_label, sub_conf = None, None

            return ClassificationResult(
                entry=entry,
                main_category=main_category,
                secondary_category=secondary_category,
                sub_category=sub_label,
                confidence_scores=confidence_scores,
                sub_confidence=sub_conf,
                processing_time=time.time()-t0,
                success=True
            )
        except Exception as e:
            return ClassificationResult(
                entry=entry,
                main_category="Unknown",
                secondary_category=None,
                success=False,
                error_message=str(e),
                processing_time=time.time()-t0
            )