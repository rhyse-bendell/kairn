from __future__ import annotations
import re
PROMPT_RE=re.compile(r"\b(instructions?|prompt|please respond|use this document|respond to|write your|fill in|complete the)\b", re.I)
def mark_prompt_flags(units: list[dict]) -> list[dict]:
    counts={}
    for u in units:
        key=(u.get('stage'), u.get('normalized_text'))
        if key[1]: counts[key]=counts.get(key,0)+1
    for u in units:
        text=u.get('text') or ''
        is_prompt=bool(PROMPT_RE.search(text))
        is_template=(counts.get((u.get('stage'), u.get('normalized_text')),0) >= 2 and len((u.get('normalized_text') or '').split()) >= 3)
        u['is_prompt']='true' if is_prompt else 'false'
        u['is_template_content']='true' if is_template else 'false'
        u['is_response']='false' if (is_prompt or is_template) else 'true'
    return units
