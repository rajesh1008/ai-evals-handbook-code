# NEW Ch16 results — ch16-full-new-2026-11-08-2131

**NEW experiment, not recovered historical.**

Budget: `{"cap_usd": 12.0, "charged_usd": 6.191862, "outstanding_reserved_usd": 0.050079, "headroom_usd": 0.05, "available_usd": 5.708059, "open_reservations": 0, "unreconciled": 8, "committed": 3396}`
Usage total: `{"calls": 3154, "in": 2135286, "out": 562964, "cost": 6.18318}`
Files: `{"agent_large": 60, "agent_small": 60, "agent_small_calc": 60, "alt_replies": 80, "judge": 2476, "replies": 318, "spanish": 100}`

## Judge metrics (from NEW raw caches)
```json
{
  "test_j0": {
    "tp": 0,
    "tn": 3,
    "fp": 0,
    "fn": 0,
    "tpr": null,
    "tnr": 1.0,
    "n": 200,
    "verdicts": {
      "cannot_tell": 197,
      "pass": 3
    }
  },
  "test_v0": {
    "tp": 37,
    "tn": 104,
    "fp": 43,
    "fn": 0,
    "tpr": 1.0,
    "tnr": 0.7074829931972789,
    "n": 200,
    "verdicts": {
      "fail": 80,
      "pass": 104,
      "cannot_tell": 16
    }
  },
  "test_v1_small_r0": {
    "tp": 52,
    "tn": 147,
    "fp": 1,
    "fn": 0,
    "tpr": 1.0,
    "tnr": 0.9932432432432432,
    "n": 200,
    "verdicts": {
      "pass": 147,
      "fail": 53
    }
  },
  "test_v1_large": {
    "tp": 52,
    "tn": 147,
    "fp": 1,
    "fn": 0,
    "tpr": 1.0,
    "tnr": 0.9932432432432432,
    "n": 200,
    "verdicts": {
      "pass": 147,
      "fail": 53
    }
  },
  "test_v1_think": {
    "tp": 52,
    "tn": 148,
    "fp": 0,
    "fn": 0,
    "tpr": 1.0,
    "tnr": 1.0,
    "n": 200,
    "verdicts": {
      "pass": 148,
      "fail": 52
    }
  },
  "test_verdict_only": {
    "tp": 51,
    "tn": 140,
    "fp": 8,
    "fn": 1,
    "tpr": 0.9807692307692307,
    "tnr": 0.9459459459459459,
    "n": 200,
    "verdicts": {
      "pass": 141,
      "fail": 59
    }
  },
  "test_tone": {
    "tp": 51,
    "tn": 79,
    "fp": 68,
    "fn": 1,
    "tpr": 0.9807692307692307,
    "tnr": 0.5374149659863946,
    "n": 200,
    "verdicts": {
      "pass": 80,
      "fail": 119,
      "cannot_tell": 1
    }
  },
  "test_v1_spanish": {
    "tp": 29,
    "tn": 71,
    "fp": 0,
    "fn": 0,
    "tpr": 1.0,
    "tnr": 1.0,
    "n": 100,
    "verdicts": {
      "pass": 71,
      "fail": 29
    }
  }
}
```

## Agent
```json
{
  "agent_small": {
    "n": 60,
    "tools": 120,
    "usage": {
      "calls": 60,
      "in": 157384,
      "out": 29340,
      "cost": 0.304084
    },
    "mean_latency": 7.471133333333333
  },
  "agent_large": {
    "n": 60,
    "tools": 120,
    "usage": {
      "calls": 60,
      "in": 157494,
      "out": 32926,
      "cost": 0.966372
    },
    "mean_latency": 10.932649999999999
  },
  "agent_small_calc": {
    "n": 60,
    "tools": 177,
    "usage": {
      "calls": 60,
      "in": 263005,
      "out": 29223,
      "cost": 0.40912
    },
    "mean_latency": 5.9899000000000004
  }
}
```
