from dataclasses import dataclass

try:
    from zxcvbn import zxcvbn as _zxcvbn
except ImportError:
    _zxcvbn = None


@dataclass
class StrengthResult:
    score: int  # 0-4
    label: str
    feedback: str
    acceptable: bool


_LABELS = {
    0: "очень слабый",
    1: "слабый",
    2: "средний",
    3: "хороший",
    4: "отличный",
}


def check_password_strength(password: str) -> StrengthResult:
    if _zxcvbn is None:
        acceptable = len(password) >= 14
        return StrengthResult(
            score=3 if acceptable else 1,
            label="хороший" if acceptable else "слабый",
            feedback="Установите zxcvbn для точной оценки",
            acceptable=acceptable,
        )

    result = _zxcvbn(password)
    score = result["score"]
    hints = result.get("feedback", {}).get("warning") or ""
    suggestions = result.get("feedback", {}).get("suggestions") or []
    extra = "; ".join(suggestions[:2])
    feedback = hints or extra or "Используйте длинную уникальную фразу"
    return StrengthResult(
        score=score,
        label=_LABELS.get(score, "неизвестно"),
        feedback=feedback,
        acceptable=score >= 2,
    )


def format_strength(password: str) -> str:
    s = check_password_strength(password)
    bars = "█" * (s.score + 1) + "░" * (4 - s.score)
    status = "✅" if s.acceptable else "⚠️"
    return f"{status} Надёжность: {s.label} [{bars}]\n💡 {s.feedback}"
