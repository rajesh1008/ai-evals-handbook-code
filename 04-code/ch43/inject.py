"""Failure injection entrypoint for Ch43."""
from lab import main
if __name__ == "__main__":
    p = main()
    inj = p["inject"]
    assert inj["detect"] and inj["gate_changed"], inj
    print("inject_ok", inj["platform"], "pinned_admit", inj["pinned"]["admit"], "drifted_admit", inj["drifted"]["admit"])
