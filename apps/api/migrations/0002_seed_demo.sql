-- Agent Flight Recorder — demo seed (GENERATED from fixtures/demo_login_flow.json).
-- Idempotent. Mirrors the REPLAY fixture so the live Supabase path and the
-- replay path agree. Run AFTER 0001_init.sql once DATABASE_URL works.
-- eval_cases has no natural unique key; clear demo rows so re-apply is idempotent.
DELETE FROM eval_cases WHERE task_name = 'demo_login_flow';

INSERT INTO runs (id, task_name, run_status, app_version, capture_session_id, rtstream_id, started_at, ended_at)
VALUES ('11111111-1111-4111-8111-111111111111','demo_login_flow','success','v1','cap-replay-success','rts-replay-success-display','2026-05-17T03:00:00Z','2026-05-17T03:00:30Z')
ON CONFLICT (id) DO NOTHING;
INSERT INTO runs (id, task_name, run_status, app_version, capture_session_id, rtstream_id, started_at, ended_at)
VALUES ('22222222-2222-4222-8222-222222222222','demo_login_flow','failure','v1','cap-replay-failure','rts-replay-failure-display','2026-05-17T03:05:00Z','2026-05-17T03:05:30Z')
ON CONFLICT (id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-000',0.0,'display','Landing page of the Acme demo SaaS dashboard is shown with a prominent ''Sign in'' button in the top right.',NULL,'{"event_id": "evt-s-000", "t_offset_s": 0.0, "channel": "display", "template_tag": null, "description": "Landing page of the Acme demo SaaS dashboard is shown with a prominent ''Sign in'' button in the top right."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-005',5.0,'display','The login page has loaded showing an email input field and a password input field with a ''Sign in'' submit button.',NULL,'{"event_id": "evt-s-005", "t_offset_s": 5.0, "channel": "display", "template_tag": null, "description": "The login page has loaded showing an email input field and a password input field with a ''Sign in'' submit button."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-010',10.0,'display','The user types the email address demo@acme.test into the email field. The email field shows a valid-format checkmark.',NULL,'{"event_id": "evt-s-010", "t_offset_s": 10.0, "channel": "display", "template_tag": null, "description": "The user types the email address demo@acme.test into the email field. The email field shows a valid-format checkmark."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-015',15.0,'display','The user types the correct password into the password field. The password strength indicator reads ''strong'' and no validation error is shown.',NULL,'{"event_id": "evt-s-015", "t_offset_s": 15.0, "channel": "display", "template_tag": null, "description": "The user types the correct password into the password field. The password strength indicator reads ''strong'' and no validation error is shown."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-020',20.0,'display','The user clicks the ''Sign in'' button. A brief inline spinner appears on the button.',NULL,'{"event_id": "evt-s-020", "t_offset_s": 20.0, "channel": "display", "template_tag": null, "description": "The user clicks the ''Sign in'' button. A brief inline spinner appears on the button."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-025',25.0,'display','Authentication succeeded. The app redirects away from the login page toward the dashboard route.',NULL,'{"event_id": "evt-s-025", "t_offset_s": 25.0, "channel": "display", "template_tag": null, "description": "Authentication succeeded. The app redirects away from the login page toward the dashboard route."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('11111111-1111-4111-8111-111111111111','evt-s-030',30.0,'display','The authenticated dashboard is fully loaded showing the welcome banner ''Welcome back, Demo'' and the account metrics widgets.',NULL,'{"event_id": "evt-s-030", "t_offset_s": 30.0, "channel": "display", "template_tag": null, "description": "The authenticated dashboard is fully loaded showing the welcome banner ''Welcome back, Demo'' and the account metrics widgets."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-000',0.0,'display','Landing page of the Acme demo SaaS dashboard is shown with a prominent ''Sign in'' button in the top right.',NULL,'{"event_id": "evt-f-000", "t_offset_s": 0.0, "channel": "display", "template_tag": null, "description": "Landing page of the Acme demo SaaS dashboard is shown with a prominent ''Sign in'' button in the top right."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-005',5.0,'display','The login page has loaded showing an email input field and a password input field with a ''Sign in'' submit button.',NULL,'{"event_id": "evt-f-005", "t_offset_s": 5.0, "channel": "display", "template_tag": null, "description": "The login page has loaded showing an email input field and a password input field with a ''Sign in'' submit button."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-010',10.0,'display','The user types the email address demo@acme.test into the email field. The email field shows a valid-format checkmark.',NULL,'{"event_id": "evt-f-010", "t_offset_s": 10.0, "channel": "display", "template_tag": null, "description": "The user types the email address demo@acme.test into the email field. The email field shows a valid-format checkmark."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-015',15.0,'display','The user mistypes the password into the password field, entering an extra character so the value no longer matches the account credentials. No client-side error is shown yet.',NULL,'{"event_id": "evt-f-015", "t_offset_s": 15.0, "channel": "display", "template_tag": null, "description": "The user mistypes the password into the password field, entering an extra character so the value no longer matches the account credentials. No client-side error is shown yet."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-020',20.0,'display','The user clicks the ''Sign in'' button. A brief inline spinner appears on the button.',NULL,'{"event_id": "evt-f-020", "t_offset_s": 20.0, "channel": "display", "template_tag": null, "description": "The user clicks the ''Sign in'' button. A brief inline spinner appears on the button."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-025',25.0,'display','Authentication failed. A red error banner reading ''Invalid email or password'' appears above the form and the password field is highlighted in red.','auth_failure','{"event_id": "evt-f-025", "t_offset_s": 25.0, "channel": "display", "template_tag": "auth_failure", "description": "Authentication failed. A red error banner reading ''Invalid email or password'' appears above the form and the password field is highlighted in red."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO events (run_id, event_id, t_offset_s, channel, description, template_tag, raw)
VALUES ('22222222-2222-4222-8222-222222222222','evt-f-030',30.0,'display','The user is still on the login page. The password field has been cleared and the red ''Invalid email or password'' error banner is still visible. Login did not complete.','auth_failure','{"event_id": "evt-f-030", "t_offset_s": 30.0, "channel": "display", "template_tag": "auth_failure", "description": "The user is still on the login page. The password field has been cleared and the red ''Invalid email or password'' error banner is still visible. Login did not complete."}'::jsonb)
ON CONFLICT (run_id, event_id) DO NOTHING;
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'where did login first go wrong',ARRAY['evt-f-015','evt-f-025','evt-f-030'],'Canonical divergence: password mistyped at t=15; auth_failure surfaces at t=25.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'show the authentication failure',ARRAY['evt-f-025','evt-f-030'],'Retrieval target = the auth_failure-tagged scenes.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'what did the user type into the password field',ARRAY['evt-f-015'],'Should rank the password-entry scene first.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'when did the invalid password error banner appear',ARRAY['evt-f-025','evt-f-030'],'Invalid-credentials banner scenes.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'find the moment the password was mistyped',ARRAY['evt-f-015'],'Stemmed match mistyped→mistype.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'is the user still on the login page at the end',ARRAY['evt-f-030'],'Final stuck state.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'show the red error banner above the form',ARRAY['evt-f-025','evt-f-030'],'Error banner visible scenes.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'where was the email address entered',ARRAY['evt-f-010'],'Email-entry scene.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'when was the sign in button clicked',ARRAY['evt-f-020'],'Submit click scene.');
INSERT INTO eval_cases (task_name, success_run_id, failure_run_id, human_divergence_s, query_text, expected_shot_ids, notes)
VALUES ('demo_login_flow','11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',15.0,'what is the final state of the failed run',ARRAY['evt-f-030'],'Terminal failed scene.');
