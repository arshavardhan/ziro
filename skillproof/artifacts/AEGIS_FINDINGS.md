# AegisAI source findings

Repository: https://github.com/arshavardhan/AegisAi

Fixed commit: `79112160653cc38cdcbddaf578e29ecfbd58a70a`.

This is a deterministic source baseline, not a completed candidate verification. The full machine-readable report contains 383 findings across 52 text files, 33 commits, and 121 statically discovered test functions. Docker is unavailable here: execution is **NOT PERFORMED**, with pass/fail counts unavailable.

| Finding | Source | Interpretation |
|---|---|---|
| Normalized Shannon entropy | `aegis/uncertainty/entropy.py:34–122`, `EntropyEstimator.compute` | Implementation handles zero probabilities and normalizes by maximum entropy. Related tests import this module. |
| Entropy enters trust scoring | `aegis/core/pipeline.py:139–250`, particularly line 214 | The static graph traces `EntropyEstimator.compute` output into the `entropy` argument of `TrustScorer.compute`. This is an assignment-based inference, not a runtime observation. |
| Trust input conversion | `aegis/scoring/trust.py:82–148`, `TrustScorer.compute` | Converts entropy to uncertainty in `ScoreInputs`; OOD classification can force maximum normalized OOD risk. |
| Score aggregation | `aegis/scoring/aggregator.py:88–137`, `ScoreAggregator.aggregate` | Uses positive confidence and inverted uncertainty/OOD/drift risk, then clips the score. Related test files are found. |
| Drift detector exists separately | `aegis/drift/data_drift.py:54–93`, `DataDriftDetector.score` | Implements per-feature KS comparisons. The inspected prediction pipeline does not supply drift to `trust.compute`; default drift weight is zero. Existence is distinct from pipeline integration. |
| Placeholder wrapper probabilities | `aegis/wrappers/openai_wrapper.py:113–130`, `OpenAIWrapper.predict_proba` | Returns a one-class placeholder array. This is partial functionality, not compatible classification probability evidence for the pipeline's two-class minimum. |
| Planned embeddings | `aegis/wrappers/openai_wrapper.py:168–180`, `OpenAIWrapper.embedding` | Raises `NotImplementedError`; marked PLANNED rather than implemented. |

Similarity findings are internal indicators with explicit limitations. Git metadata records repository progression, not verified candidate authorship. Five human-authored draft questions grounded in these source locations are in `aegis-draft-viva.json`; no candidate answers have been invented.

To complete live verification, configure the provider and submit `aegis-request.json`, answer the generated viva, then have a reviewer inspect the report and explicitly approve or reject. The baseline's live-model call count is zero. Synthetic API tests exercise the loop separately and must not be confused with this real-source baseline.
