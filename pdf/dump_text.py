"""Same dump as the TypeScript port, for the cross-language diff."""
import json, sys
from enneagram_manual.content import ARCHETYPES, LENSES
from enneagram_manual.document import build_document
from enneagram_manual.models import build_profile

out = {}
for slug in sorted(LENSES):
    for type_id in sorted(ARCHETYPES):
        scores = {t: 1 for t in ARCHETYPES}
        scores[type_id] = 7
        scores[(type_id % 9) + 1] = 3
        p = build_profile(scores=scores, relationship=slug)
        d = build_document(p)
        out[f"{slug}/type-{type_id}"] = {
            "core": p.core, "secondary": p.secondary, "wing": p.wing,
            "blend_mode": p.blend_mode, "confidence": p.confidence, "seed": p.seed,
            "sections": [{"n": s.number, "title": s.title, "text": d.text_of(s)} for s in d.sections],
        }
sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=1))
