# Failure Modes — GTM Lane

Phase 2.4. Column convention matches `engineering-lane.md`.

| Condition | Detection | Recovery | failure_code | Who resolves |
|---|---|---|---|---|
| Postiz auth expired | `preflight_gtm.sh` Postiz call | Lane `blocked:postiz_auth_expired`; morning briefing surfaces | `postiz_auth_expired` | Founder rotates key in Keychain/.env |
| Gemini quota hit | Runner catches quota error from client | Task re-queued with `status=blocked`; budget cap in `gtm_cooldowns.py` | `gemini_quota_exceeded` | Founder |
| Account warming cooldown | `packages/policies/gtm_cooldowns.py` gap check | Task re-scheduled to next allowed slot | `gtm_cooldown_active` | GTM worker (auto) |
| Post rejected by platform | Postiz response non-2xx with rejection code | Result `failed`, reason attached; retry policy = 0 | `platform_post_rejected` | Founder / content review |
| Analytics fetch failure | Observability rollup catches exception | Briefing marks metrics as stale; rollup continues | `gtm_analytics_fetch_failed` | GTM worker (auto retry) |
| Credential rotation mid-task | Secrets helper returns None mid-run | `GtmFrozenError` analog: task re-queued as `paused:creds_rotation` | `gtm_credential_rotation` | Founder |
| Kill switch engaged | `is_gtm_frozen(ROOT)` true | Worker sleeps; mid-task raises `GtmFrozenError`; re-queued as `paused:frozen` | `gtm_frozen` | Founder runs `gtm_unfreeze.sh` |
| Threat-model drift | `check_threat_model_drift` non-None | Lane `blocked:threat-model-drift` | `gtm_threat_model_drift` | Founder runs `acknowledge_threat_model.sh --read` |
| creator-outreach-draft auto-send attempted | Lint on draft outputs; failure-mode grep in repo | Immediate lane halt; emits regression capture | `gtm_outreach_auto_send_attempt` | Founder (investigate) |
| Off-voice draft escaped guardrail | `content-voice-guardrail` fixtures failed | Task `failed`, briefing surfaces pattern | `content_voice_guardrail_fail` | GTM worker |
| social-post-safety hard gate fail | validator returns `fail` | Task blocked pre-schedule | `social_post_safety_block` | GTM worker / founder |

Environmental-only rows (`postiz_auth_expired`, `gemini_quota_exceeded`,
`gtm_credential_rotation`) use `no_test_reason_code=environmental_only`.
