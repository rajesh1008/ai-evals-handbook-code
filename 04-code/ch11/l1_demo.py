import json, sys; sys.path.insert(0, "../truss")
from truss import fields as F
from specs import SPECS
raw = {j["id"]: j["raw"] for j in map(json.loads, open("out/extract-haiku.jsonl"))}
parsed = {i: F.parse_json(r) for i, r in raw.items()}
print("strict JSON:", sum(o is not None and not rep for o, rep in parsed.values()), "of", len(raw))
obj, repaired = parsed["hd-0003"]
print("hd-0003 needed the fence repair:", repaired)
print(F.layer_one(obj, SPECS))
