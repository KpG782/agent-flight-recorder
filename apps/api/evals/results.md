# Agent Flight Recorder — Eval Results

Cases: **10** · task `demo_login_flow` (success vs. mistyped-password failure).

## Metrics

| Metric | Value |
|---|---|
| Retrieval precision@3 (mean) | **0.367** (ceiling ≈0.33 — most cases have a single relevant shot) |
| Retrieval recall@3 (mean) | **0.783** |
| Top-1 retrieval accuracy | **0.900** |
| Time-to-first-evidence (`/compare`) | **0.4 ms** |
| Mean `/search` latency | 0.3 ms |
| Divergence error vs. human label | **0.00 s** |
| Divergence accurate (≤5s) | **yes** |

## Per-case retrieval

| Query | Expected | Top-3 returned | P@3 | Top-1 |
|---|---|---|---|---|
| where did login first go wrong | `evt-f-015,evt-f-025,evt-f-030` | `evt-f-030,evt-f-005,evt-f-000` | 0.33 | ✓ |
| show the authentication failure | `evt-f-025,evt-f-030` | `evt-f-025,evt-f-020,evt-f-000` | 0.33 | ✓ |
| what did the user type into the password field | `evt-f-015` | `evt-f-015,evt-f-030,evt-f-010` | 0.33 | ✓ |
| when did the invalid password error banner appear | `evt-f-025,evt-f-030` | `evt-f-030,evt-f-025,evt-f-015` | 0.67 | ✓ |
| find the moment the password was mistyped | `evt-f-015` | `evt-f-015,evt-f-005,evt-f-030` | 0.33 | ✓ |
| is the user still on the login page at the end | `evt-f-030` | `evt-f-030,evt-f-005,evt-f-020` | 0.33 | ✓ |
| show the red error banner above the form | `evt-f-025,evt-f-030` | `evt-f-025,evt-f-030,evt-f-015` | 0.67 | ✓ |
| where was the email address entered | `evt-f-010` | `evt-f-010,evt-f-005,evt-f-025` | 0.33 | ✓ |
| when was the sign in button clicked | `evt-f-020` | `evt-f-020,evt-f-000,evt-f-005` | 0.33 | ✓ |
| what is the final state of the failed run | `evt-f-030` | `evt-f-025,evt-f-005,evt-f-020` | 0.00 | · |

