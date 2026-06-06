"""Generate customer follow-up questions for incomplete plush briefs."""
from __future__ import annotations

from typing import Any


FIELD_QUESTIONS = {
    "target_height": "请确认成品高度是 20cm、30cm，还是其他尺寸？",
    "body_proportions": "请确认头身比例希望更接近原图，还是更可爱的 Q 版比例？",
    "materials": "请确认主要面料偏好：短毛绒、长毛绒、水晶超柔，还是由我们按效果建议？",
    "accessories": "请确认包包、帽子、花朵等配件是否需要做成独立软布配件？",
    "key_features_to_preserve": "请确认最不能丢失的辨识特征是哪几个？",
    "forbidden_changes": "请确认哪些内容绝对不能改动，例如发型、服装颜色、表情或配件？",
}


def build_pending_questions(structured: dict[str, Any], risk_notes: list[str]) -> list[str]:
    questions: list[str] = []
    for field, question in FIELD_QUESTIONS.items():
        if not structured.get(field):
            questions.append(question)

    if any("Multiple material" in note for note in risk_notes):
        questions.append("多张参考素材中，请确认哪一张作为主参考，其他素材作为补充？")
    if structured.get("source_type") in {"real_person_photo", "mixed"}:
        questions.append("真人照片转毛绒公仔时，表情和发型是否需要更卡通、更幼态？")
    if structured.get("source_type") in {"poster", "ip_character", "reference_image"}:
        questions.append("复杂图案或小文字是否可以简化成刺绣符号或色块？")

    return list(dict.fromkeys(questions))
