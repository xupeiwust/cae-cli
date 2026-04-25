# CAE CLI Fine-tune Dataset v2

This dataset was exported from local project assets:

- `tests/fixtures/diagnosis_cases` (high-confidence expected labels)
- `results/*` solver logs and smoke outputs
- `tests/test_mcp_server.py` status reasons and guarded operation patterns
- `DEVELOPMENT_LOG.md` guarded executor capability milestones
- `examples/*` solver smoke input files
- deterministic policy augmentations aligned to solver status routing and guarded write boundaries

## Summary

- record_count: 291
- split_counts: {"test": 34, "train": 221, "val": 36}
- task_type_counts: {"capability_grounding": 1, "fixture_route_mapping": 33, "guarded_executor_decision": 2, "guarded_executor_decision_augmented": 16, "issue_key_extraction": 11, "smoke_input_profiling": 5, "smoke_input_profiling_augmented": 30, "solver_route_decision": 4, "solver_route_decision_augmented": 32, "status_reason_routing": 13, "status_reason_routing_augmented": 104, "status_route_policy": 40}
- source_group_counts: {"development_log": 1, "results_logs": 36, "routing_policy": 40, "solver_smoke_case": 35, "tests_fixture": 44, "tests_guarded_operations": 18, "tests_status_reason": 117}

## Files

- `all.jsonl`: full rich records with metadata and `messages`
- `train.jsonl`, `val.jsonl`, `test.jsonl`: rich split records
- `train_chat.jsonl`, `val_chat.jsonl`, `test_chat.jsonl`: chat-only records for common finetune toolchains
- `train_hq.jsonl`, `val_hq.jsonl`, `test_hq.jsonl`: rich high-quality subset (quality_score >= 0.9)
- `train_hq_chat.jsonl`, `val_hq_chat.jsonl`, `test_hq_chat.jsonl`: chat-only high-quality subset
- `manifest.json`: counts and quality filter metadata
- `manifest_hq.json`: high-quality subset counts and threshold
