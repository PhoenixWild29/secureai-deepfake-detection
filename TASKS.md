# Proposed Follow-up Tasks

## Typo Fix
- **Issue**: The console message in `test_videos.py` reports "Authenticity Score: <value>/100" even though the score is already a 0-1 fraction, so the "/100" suffix is a typo that misleads users about the score scale. 【F:test_videos.py†L59-L87】
- **Task**: Update the output string to format the authenticity score correctly (e.g., convert to percentage or remove the erroneous "/100" text).

## Bug Fix
- **Issue**: The CLI output in `ai_model/detect.py` prints literal strings like `.2%` and `.2f` instead of formatted metrics when benchmarking models, due to missing f-strings/format specifiers. 【F:ai_model/detect.py†L129-L155】
- **Task**: Replace the placeholder strings with actual formatted outputs (e.g., use `print(f"  Confidence: {r['confidence']:.2%}")`).

## Documentation/Comment Discrepancy
- **Issue**: The `detect_fake` docstring advertises support for a `"yolo"` model type that the implementation does not handle (and omits the default `"resnet"` option). 【F:ai_model/detect.py†L23-L66】
- **Task**: Align the docstring with the actual supported model types by removing or clarifying the nonexistent `"yolo"` option and documenting `"resnet"`.

## Test Improvement
- **Issue**: `test_system.py` is framed as a test but only prints status messages and returns booleans without assertions, so it cannot fail under automated test runners. 【F:test_system.py†L1-L58】
- **Task**: Convert the script into a proper unit/integration test that asserts expected outcomes (e.g., verify `main` completes without raising and returns expected data) so failures are reported automatically.
