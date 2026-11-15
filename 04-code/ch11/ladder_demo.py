import sys; sys.path.insert(0, "../truss")
from truss import fields as F
for tol in (0.005, 1.00):
    spec = F.FieldSpec("payroll_total", "money", tolerance=tol)
    print(f"hd-0180 total, tolerance ${tol:.3f}:", F.outcome(spec, "4,602.66", 4603.66))
emp = F.FieldSpec("employer", "name", match="prefix")
for got in ("TEMPE HOME HEALTH LLC", "TEMPE HOMEHEALTH LLC", "Tempe Home Health PA"):
    print(f"{got!r:26} ->", F.normalise(emp, got), "|", F.outcome(emp, got, "Tempe Home Health"))
print("'10/05/2027' ->", F.to_date("10/05/2027"), "| '10 de mayo de 2027' ->", F.to_date("10 de mayo de 2027"))
