# Confidence calibration

## What “confidence” means in API responses

The **confidence** value in detection results is **not** a statistically calibrated probability (e.g. “80% confident” does not mean “correct 80% of the time when we say 80%”). By default it is **agreement strength**: how far the ensemble’s probability is from 0.5 (uncertain).

- **0** = model is uncertain (probability near 0.5)  
- **1** = model is very decisive (probability near 0 or 1)

So it answers: *“How decisive is the model?”* not *“How often is it right?”*.

---

## Default: agreement strength

Default formula:

```text
confidence = abs(ensemble_fake_probability - 0.5) * 2
```

So:

- `ensemble_fake_probability = 0.5` → `confidence = 0` (uncertain)
- `ensemble_fake_probability = 0.0` or `1.0` → `confidence = 1.0` (very decisive)

This is **agreement strength**, not calibrated confidence. The API and detectors expose this as the default so behaviour is clear and consistent.

---

## Optional: temperature scaling

You can make the reported confidence **less overconfident** using temperature scaling (no validation set required):

- **Environment variables**
  - `CONFIDENCE_CALIBRATION=temperature` – use temperature scaling.
  - `CONFIDENCE_TEMPERATURE=1.5` – temperature (e.g. 1.5 or 2.0; higher = more conservative).

- **Effect**  
  Probabilities are scaled so that extreme values (near 0 or 1) are pulled toward 0.5. The reported confidence then tends to be lower and can better reflect reliability when models are overconfident.

**Example (PowerShell, this session):**

```powershell
$env:CONFIDENCE_CALIBRATION = "temperature"
$env:CONFIDENCE_TEMPERATURE = "1.5"
```

Then run your API or detection script. The same `confidence` field will use temperature-scaled values.

---

## Other options

- **`CONFIDENCE_CALIBRATION=winning_prob`**  
  Confidence = probability of the predicted class (fake or real). Same as the raw ensemble probability on the winning side; not calibrated.

- **`CONFIDENCE_CALIBRATION=agreement_strength`** (default)  
  Confidence = agreement strength as above.

---

## Response field: `confidence_meaning`

When the detector returns a result, it can include **`confidence_meaning`**:

- `agreement_strength` – default; “how decisive” (distance from 0.5).
- `temperature` – temperature-scaled confidence.
- `winning_prob` – probability of the predicted class.

Use this in the UI or logs so users know how to interpret **confidence**.

---

## Summary

| Setting                         | Meaning                                      |
|---------------------------------|----------------------------------------------|
| Default (no env)                | `agreement_strength`: how decisive, not accuracy. |
| `CONFIDENCE_CALIBRATION=temperature` | Less overconfident; can better reflect reliability. |
| `CONFIDENCE_TEMPERATURE=1.5`    | Strength of temperature scaling (e.g. 1.5 or 2.0). |

For full calibration (e.g. Platt scaling on a validation set), you would need to add a separate calibration step and store parameters; the current implementation provides agreement strength by default and optional temperature scaling without a validation set.
