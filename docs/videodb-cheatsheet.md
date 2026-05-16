# VideoDB Cheatsheet

> **Status: CONFIRMED by RECON-A.** Signatures below are quoted verbatim from the
> `video-db/videodb-python` SDK source (`main` branch) and `docs.videodb.io` API
> reference (OpenAPI `.md` pages). This file is authoritative — `CAPTURE` / `INDEX` /
> `MEMORY` / `EVIDENCE` agents should not need to re-read VideoDB docs.
>
> SDK version basis: `videodb` 0.2.x (`videodb-python@main`). Install:
> `pip install "videodb[capture,websockets]"` (the `capture` extra pulls
> `videodb-capture-bin`; `websockets` is required for `WebSocketConnection`).
>
> **Confidence legend:** ✅ verified from SDK source · 🟡 verified from docs only
> (no SDK method) · ⚠️ gap / unverified — see "Gaps / unverified" at the bottom.
> Read that section before relying on items 6 and the webhook signature.

---

## 0. Object model & ID prefixes (mental model)

| Object | ID prefix | Created by | Reached via |
|---|---|---|---|
| `Connection` | — | `videodb.connect()` | top-level |
| `Collection` | `c-...` / `"default"` | `conn.get_collection()` | `conn` |
| `CaptureSession` | `cap-...` | `conn.create_capture_session()` | `conn` |
| `RTStream` (one per channel) | `rts-...` | created by capture pipeline | `cap.get_rtstream(cat)` / `coll.get_rtstream(id)` |
| `RTStreamSceneIndex` | `scene-idx-...` | `rtstream.index_visuals()/index_audio()` | `rtstream.list_scene_indexes()` |
| Event (reusable template) | `event-...` | `conn.create_event()` | `conn.list_events()` |
| Alert (event bound to a stream+channel) | `alert-...` | `scene_index.create_alert()` | `scene_index.list_alerts()` |

Lifecycle states (CaptureSession `status`):
`created → starting → active → stopping → stopped → exported` (also `failed`).
**`active` is the trigger to start indexing pipelines.**

API auth header (FYI for raw HTTP / webhook debugging): `x-access-token: sk-...`.
Base URL: `https://api.videodb.io` (staging: `https://staging-api.videodb.io`).

---

## 1. Auth / client init ✅

Env var is **`VIDEO_DB_API_KEY`** (note: *not* `VIDEODB_API_KEY` — the MASTER
naming is wrong; the SDK reads `VIDEO_DB_API_KEY`). Constant
`videodb._constants.VIDEO_DB_API = "https://api.videodb.io"`.

```python
import videodb

# connect() signature (videodb/__init__.py):
#   connect(api_key: str = None,
#           session_token: str = None,
#           base_url: Optional[str] = VIDEO_DB_API,   # "https://api.videodb.io"
#           log_level: Optional[int] = logging.INFO,
#           **kwargs) -> videodb.client.Connection

# Preferred: env var VIDEO_DB_API_KEY is read automatically
conn = videodb.connect()

# Explicit key + base URL override:
conn = videodb.connect(api_key="sk-...", base_url="https://api.videodb.io")

# Alternative auth: short-lived session token instead of api_key
conn = videodb.connect(session_token="st-...")
```

- If neither `api_key` nor `session_token` is given, `connect()` reads
  `os.environ["VIDEO_DB_API_KEY"]`; if still empty it raises
  `videodb.AuthenticationError`.
- `Connection` is an `HttpClient` subclass. **No explicit close/teardown** —
  it is a stateless REST wrapper (default `timeout=30`, `max_retries=1`,
  retries on `[502,503,504]`). Reuse one `Connection` for the process.
- Collection scope: `conn.collection_id` defaults to `"default"`.
  `coll = conn.get_collection("default")` to get a `Collection` object
  (needed for `get_rtstream` / `list_rtstreams`).

---

## 2. CaptureSession lifecycle ✅

### 2a. Create the session (backend, holds the API key)

```python
# Connection.create_capture_session(
#     end_user_id: str,
#     collection_id: str = "default",
#     callback_url: str = None,        # webhook URL for lifecycle events
#     ws_connection_id: str = None,    # bind to an existing WS connection
#     metadata: dict = None,           # custom run metadata (see item 6)
# ) -> CaptureSession
cap = conn.create_capture_session(
    end_user_id="user_abc",
    collection_id="default",
    callback_url="https://<ngrok>/webhooks/videodb",
    metadata={
        "task_name": "demo_login_flow",
        "run_id": "<uuid>",
        "run_status": "in_progress",
        "app_version": "v1",
    },
)
cap.id            # "cap-..."  -> persist as capture_session_id
cap.status        # "created"
cap.collection_id
```

### 2b. Mint a short-lived client token (never ship the API key)

```python
# Connection.generate_client_token(expires_in: int = 86400) -> str
token = conn.generate_client_token(expires_in=600)   # 600s for the demo
# Returns the raw token string ("st-..."). REST response also carries
# {"token","expires_at" (unix int),"expires_in"} — generate_client_token()
# only returns .get("token"); compute expires_at yourself if you need the
# ISO string for the /sessions/start response.
```

### 2c. Desktop capture client — multi-channel (display + mic) ✅

Runs on the **machine being recorded** (macOS/Windows only; needs
`videodb-capture-bin`). All methods are `async`.

```python
import asyncio
from videodb.capture import CaptureClient

async def run_capture(token: str, capture_session_id: str):
    # CaptureClient(client_token: str, base_url: Optional[str] = None)
    client = CaptureClient(client_token=token)

    # Valid kinds: "microphone", "screen_capture"
    await client.request_permission("microphone")
    await client.request_permission("screen_capture")

    # list_channels() -> Channels(mics, displays, system_audio, cameras)
    # each group is a ChannelList; .default == first element
    channels = await client.list_channels()
    mic = channels.mics.default          # AudioChannel, id like "mic:default"
    display = channels.displays.default  # VideoChannel, id like "display:1"

    # store=True => persist/record this channel so it can be exported & replayed
    mic.store = True
    display.store = True
    display.is_primary = True            # mark the primary video channel

    # start_session(capture_session_id, channels: List[Channel],
    #               primary_video_channel_id=None  # DEPRECATED, use is_primary)
    await client.start_session(
        capture_session_id=capture_session_id,
        channels=[mic, display],
    )

    # ... recording ...
    await client.stop_session()         # stop recording
    await client.shutdown()             # terminate the capture binary

asyncio.run(run_capture(token, cap.id))
```

Channel ID prefixes: `mic:`, `display:`/`screen:`, `system_audio:`, `camera:`.
`channel.pause()` / `channel.resume()` are available (async).
Local capture-binary events: `async for ev in client.events(): ...`.

### 2d. Retrieve the session / its RTStreams ✅

```python
# Connection.get_capture_session(session_id, collection_id="default") -> CaptureSession
cap = conn.get_capture_session("cap-...")
cap.status                 # "active" once streams are live
cap.channels               # [VideoChannel, AudioChannel, ...]
cap.displays               # video channels only
cap.rtstreams              # List[RTStream] (populated once active)

# Filter RTStreams by category. category matches RTStream.channel_id,
# use videodb.RTStreamChannelType constants:
from videodb import RTStreamChannelType   # .mic="mic" .screen="screen" .system_audio="system_audio"
mic_streams    = cap.get_rtstream(RTStreamChannelType.mic)     # List[RTStream]
screen_streams = cap.get_rtstream(RTStreamChannelType.screen)  # List[RTStream]
rts_display = screen_streams[0]
rts_mic     = mic_streams[0]

# List all sessions (e.g. to find an active run):
sessions = conn.list_capture_sessions(collection_id="default", status="active")
```

**Get an RTStream by ID directly** (used from a webhook handler that only has
`rtstream_id`) — this method is on **`Collection`, not `Connection`**:

```python
coll = conn.get_collection("default")
rts = coll.get_rtstream("rts-...")        # Collection.get_rtstream(id) -> RTStream
all_streams = coll.list_rtstreams(status="connected")  # List[RTStream]
```
> The docs show `conn.get_rtstream(...)` — that does **not** exist on
> `Connection`. Use `coll.get_rtstream(id)` or `cap.get_rtstream(category)`.

### 2e. Export the recorded session to a replayable video asset ✅

```python
# CaptureSession.export(video_channel_id=None, ws_connection_id=None) -> dict
# Poll: returns {"export_status": "exporting"} then
#       {"export_status":"exported","video_id":...,"stream_url":...,"player_url":...}
res = cap.export()
# Per-channel RTStream export (stream must be stopped first; idempotent):
# RTStream.export(name=None) -> RTStreamExportResult(video_id, stream_url,
#                                                    player_url, name, duration)
exported = rts_display.export(name="demo_login_flow - failure run")
```

---

## 3. RTStream retrieval & historical playback ✅

RTStream timestamps are **Unix epoch** (seconds for `generate_stream`,
milliseconds in WS event `start/end`). Postmortem rewind = call
`generate_stream(start, end)` with an explicit window.

```python
# RTStream.generate_stream(
#     start: int,                       # unix ts (seconds)
#     end: int,                         # unix ts (seconds)
#     player_config: Optional[Dict[str,str]] = None  # {"title","description","slug"}
# ) -> str   # RETURNS player_url; also sets rts.stream_url (HLS) + rts.player_url
player_url = rts_display.generate_stream(
    start=1_710_000_000,
    end=1_710_000_030,
    player_config={"title": "demo_login_flow — failure run"},
)
hls_url = rts_display.stream_url     # raw HLS m3u8, set as a side effect

# Embed (requires generate_stream() called first — no auto_generate for RTStream):
iframe = rts_display.get_embed_code(width="100%", height=405,
                                    title="VideoDB Player")
```

Raw REST equivalent: `GET /rtstream/{stream_id}/stream?start=<unix>&end=<unix>`
→ `{"stream_url": "..."}` (plus `player_url`). Optional query:
`original_frame_rate`, `frame_rate` (default 1).

Live transcript polling (postmortem text rewind):
```python
# RTStream.get_transcript(page=1, page_size=100, start=None, end=None,
#                          since=None, engine=None) -> dict
txt = rts_mic.get_transcript(start=1_710_000_000, end=1_710_000_030)
```

---

## 4. `index_visuals` — visual scene indexing ✅

```python
# RTStream.index_visuals(
#     prompt: str = None,
#     batch_config: dict = None,   # {"type":"time","value":<window_s>,
#                                  #  "frame_count":<frames_per_window>}
#                                  # NOTE: only "time" type is supported.
#     model_name: str = None,
#     model_config: dict = {},
#     name: str = None,
#     ws_connection_id: Optional[str] = None,  # push scene events over WS
# ) -> RTStreamSceneIndex
scene_index = rts_display.index_visuals(
    prompt=(
        "Identify visible UI elements, button clicks, page transitions, "
        "error states, modal dialogs, form submissions, and authentication "
        "screens. Be specific about what app or page is shown and any text "
        "visible."
    ),
    # MASTER cost rule: 1 frame / 5s -> window 5s, 1 frame per window:
    batch_config={"type": "time", "value": 5, "frame_count": 1},
    name="visuals",
    ws_connection_id=ws.connection_id,   # optional, for live WS scene events
)
scene_index.rtstream_index_id   # "scene-idx-..." -> persist for search/alerts
scene_index.status              # control with .start() / .stop()
```

- The **prompt is the only prompt-tuning hook** (it is sent as `prompt` in the
  POST body). `extraction_type` is forced to `"time"` (`SceneExtractionType.time_based`).
- `batch_config` is translated to `extraction_config={"time": value,
  "frame_count": frame_count}`. If `batch_config=None`, server defaults apply.
- Returns an `RTStreamSceneIndex`. Lifecycle:
  `scene_index.start()` (status → `"connected"`) / `scene_index.stop()`.
- Read indexed scenes back:
  `scene_index.get_scenes(start=None, end=None, page=1, page_size=100)` →
  `{"scenes": [...], "next_page": bool}`.
- List/get: `rts.list_scene_indexes()` → `List[RTStreamSceneIndex]`;
  `rts.get_scene_index(index_id)`.

Raw REST: `POST /rtstream/{stream_id}/index/scene` with
`{extraction_type, extraction_config, prompt, model_name, model_config, name}`.

---

## 5. `index_audio` — mic transcription / audio understanding ✅

```python
# RTStream.start_transcript(ws_connection_id: Optional[str]=None,
#                           engine: Optional[str]=None) -> dict
#   engine default server-side: "assemblyai" (transcript polling default "AAIS")
rts_mic.start_transcript(ws_connection_id=ws.connection_id)

# RTStream.index_audio(
#     prompt: str = None,
#     batch_config: dict = None,   # {"type":"word"|"sentence"|"time","value":<int>}
#     model_name: str = None,
#     model_config: dict = {},
#     name: str = None,
#     ws_connection_id: Optional[str] = None,
# ) -> RTStreamSceneIndex
audio_index = rts_mic.index_audio(
    prompt="Summarize what the user/agent said and any spoken errors or commands.",
    batch_config={"type": "sentence", "value": 1},
    name="audio",
    ws_connection_id=ws.connection_id,
)
# Stop transcription:  rts_mic.stop_transcript()
```

- `index_audio` runs on the **transcript** (`extraction_type` forced to
  `SceneExtractionType.transcript`). `batch_config` → `extraction_config=
  {"segmenter": type, "segmentation_value": value}`.
- Sibling: `RTStream.index_spoken_words(prompt=None,
  segmenter=Segmenter.word, length=10, model_name=None, model_config={},
  name=None, ws_connection_id=None)` — same endpoint, segmenter is one of
  `Segmenter.word|sentence|time`.
- `start_transcript()` must be running for `index_audio` to have a transcript.

---

## 6. Scene-level custom metadata (`task_id`, `run_status`, `divergence_point`) ⚠️ PARTIAL

**There is no SDK call to attach arbitrary custom metadata to live RTStream
scene records.** `RTStreamSceneIndex.get_scenes()` records and
`RTStreamShot` only carry `start`, `end`, `text`, `score`, `scene_index_id`,
`scene_index_name`, and a server-populated `metadata` field. The SDK never
sends a user metadata dict on the index/scene path for RTStreams.

Use these confirmed mechanisms instead:

1. **Run-level metadata on the CaptureSession** (the correct home for
   `task_name`, `run_id`, `run_status`, `app_version`):
   ```python
   cap = conn.create_capture_session(end_user_id="...",
       metadata={"task_name":"demo_login_flow","run_id":"<uuid>",
                 "run_status":"in_progress","divergence_point":None})
   conn.get_capture_session(cap.id).metadata   # read back
   ```
   (Mutating metadata after creation has no documented SDK setter — treat the
   creation-time dict as authoritative; persist `run_status` / `divergence_point`
   transitions in Supabase per `architecture.md`.)

2. **Distinct scene-index `name` per concern** to segment by meaning, e.g.
   `index_visuals(name="ui_events")`, then `rtstream.search(query, index_id=...)`.

3. **`metadata` filter on search** is supported (see item 7) — if the server
   attaches metadata to records, filter via
   `rtstream.search(query, filter=[{...}])`. The *shape* of filter dicts is
   undocumented (see Gaps).

4. **`Scene.metadata` (uploaded-video path only):** `videodb.scene.Scene`
   has a `metadata: dict` field and `to_json()` serializes it — but this is
   the **uploaded-Video** scene-indexing path, **not** the live RTStream
   pipeline this project uses. Do not rely on it for capture runs.

> Practical guidance for MEMORY/EVIDENCE: keep `task_id`/`run_status`/
> `divergence_point` in Supabase keyed by `run_id`, and correlate to VideoDB
> by `capture_session_id` + `rtstream_id` + timestamps. Do **not** assume
> per-scene custom metadata round-trips through VideoDB.

---

## 7. Search — keyword + semantic ✅

### 7a. RTStream search (the path this project uses)

```python
# RTStream.search(
#     query: str,
#     index_id: Optional[str] = None,            # -> "scene_index_id" filter
#     result_threshold: Optional[int] = None,    # == k (number of results)
#     score_threshold: Optional[float] = None,   # min relevance score
#     dynamic_score_percentage: Optional[float] = None,
#     filter: Optional[List[Dict[str,Any]]] = None,  # metadata filters
# ) -> RTStreamSearchResult
res = rts_display.search(
    query="where did login fail",
    index_id=scene_index.rtstream_index_id,
    result_threshold=3,          # this is "k"
    score_threshold=0.2,
)
for shot in res.get_shots():     # List[RTStreamShot]
    shot.rtstream_id
    shot.start          # Unix timestamp (float)
    shot.end            # Unix timestamp (float)
    shot.text           # indexed description
    shot.search_score   # relevance score (float, server "score")
    shot.scene_index_id
    shot.metadata       # server-populated metadata (may be None)
```

`RTStreamSearchResult(collection_id, shots: List[RTStreamShot])`.
Raw REST: `POST /rtstream/{stream_id}/search`, body
`{query, scene_index_id, result_threshold(default 10), score_threshold,
dynamic_score_percentage(default 20), stitch(default true), filter, rerank,
rerank_params}`. Response `data.results[]` items:
`{start, end, text, score, scene_index_id}` (timestamps are Unix).

### 7b. Collection / uploaded-video search (semantic + keyword) ✅

```python
# Collection.search(query, search_type=SearchType.semantic,
#   index_type=IndexType.spoken_word, result_threshold=None,
#   score_threshold=None, dynamic_score_percentage=None) -> SearchResult
from videodb import SearchType, IndexType
# SearchType.semantic="semantic"  SearchType.keyword="keyword"
# IndexType.spoken_word="spoken_word"  IndexType.scene="scene"
res = coll.search("login error", search_type=SearchType.semantic,
                  index_type=IndexType.scene, result_threshold=3)
```
Semantic defaults (`SemanticSearchDefaultValues`): `result_threshold=5`,
`score_threshold=0.2`. **Keyword search is video-only**:
`KeywordSearch.search_inside_collection` raises `NotImplementedError`
("Keyword search will be implemented in the future"). For this project use
**RTStream semantic search (7a)** — keyword/collection scene search inside a
collection is not implemented in the SDK.

`SearchResult.get_shots()` → `List[Shot]` with `.video_id .start .end .text
.search_score .scene_index_id .metadata .stream_url .player_url`.

---

## 8. Compile search results into a playable stream ✅

### 8a. Uploaded-video `SearchResult` (collection path)

```python
# SearchResult.compile() -> str (stream_url); also sets .player_url
stream_url = res.compile()        # POST /compile, body is a list of
                                  # {"video_id","collection_id","shots":[(s,e)]}
res.play()                        # compile() + open in browser
res.get_embed_code(auto_generate=True)   # iframe; auto-compiles
```

### 8b. RTStream evidence clip with a ±window around a timestamp ✅ (recommended for this project)

There is no `compile()` on `RTStreamSearchResult`. Build the evidence clip by
bounding a window around the divergence Unix timestamp and calling
`generate_stream` (timestamps are **Unix epoch seconds**):

```python
WINDOW_S = 10
divergence_ts = int(shot.start)          # Unix ts from a RTStreamShot

clip_player_url = rts_display.generate_stream(
    start=divergence_ts - WINDOW_S,
    end=divergence_ts + WINDOW_S,
    player_config={"title": "divergence ±10s"},
)
clip_hls = rts_display.stream_url        # m3u8 for the bounded window

# Single-shot helper: each RTStreamShot can stream just its own span
shot.generate_stream()    # GET /rtstream/{id}/stream?start=int(start)&end=int(end)
shot.stream_url ; shot.player_url
```

> EVIDENCE compiler pattern: run `rts.search(...)` → take `shot.start` as the
> divergence timestamp → `rts.generate_stream(start-W, end+W)` per run →
> return both `player_url`s. This satisfies primitive #4.

---

## 9. Webhook payload schema 🟡 (docs-verified; SDK has no verifier)

Two distinct webhook payload families. Both delivered via the
`callback_url` you pass (CaptureSession `callback_url`, or alert `callback_url`).

### 9a. CaptureSession lifecycle envelope (from `create_capture_session(callback_url=...)`)

```json
{
  "version": "2",
  "event": "capture_session.active",
  "timestamp": "2026-01-20T12:34:56Z",
  "capture_session_id": "cap-xxx",
  "end_user_id": "user_abc",
  "status": "active",
  "data": {}
}
```

Lifecycle events & key `data`:

| `event` | `status` | `data` |
|---|---|---|
| `capture_session.created` | created | — |
| `capture_session.starting` | starting | — |
| `capture_session.active` | active | `rtstreams[]` |
| `capture_session.stopping` | stopping | — |
| `capture_session.stopped` | stopped | — |
| `capture_session.exported` | exported | `exported_video_id` |
| `capture_session.failed` | failed | `error` object |

`capture_session.active` payload (this is where you start pipelines):
```json
{
  "event": "capture_session.active",
  "capture_session_id": "cap-xxx",
  "status": "active",
  "data": { "rtstreams": [
    { "rtstream_id": "rts-1", "name": "mic:default",          "media_types": ["audio"] },
    { "rtstream_id": "rts-2", "name": "system_audio:default",  "media_types": ["audio"] },
    { "rtstream_id": "rts-3", "name": "display:1",             "media_types": ["video"] }
  ]}
}
```
Handler pattern:
```python
def on_active_webhook(payload):
    coll = conn.get_collection("default")
    for r in payload["data"]["rtstreams"]:
        rts = coll.get_rtstream(r["rtstream_id"])
        if "audio" in r["media_types"]:
            rts.start_transcript()
            rts.index_audio(prompt="...")
        if "video" in r["media_types"]:
            rts.index_visuals(prompt="...")
```

### 9b. Alert / event-trigger payload (from `scene_index.create_alert(callback_url=...)`)

```json
{
  "event_id": "event-3fd4174feceb6162",
  "label": "traffic_violation",
  "confidence": 0.95,
  "explanation": "A red sedan ran through the intersection ...",
  "timestamp": "2024-01-15T10:30:45Z",
  "start_time": 1234.5,
  "end_time": 1238.0,
  "stream_url": "https://stream.videodb.io/v3/...",
  "player_url": "https://console.videodb.io/player?url=..."
}
```
| Field | Type | Meaning |
|---|---|---|
| `event_id` | string | ID of the triggered event (the `event-...` template) |
| `label` | string | Human-readable event label |
| `confidence` | float 0–1 | Detection confidence |
| `explanation` | string | AI description of what matched |
| `timestamp` | string | ISO 8601 |
| `start_time` / `end_time` | float | Clip bounds (seconds) |
| `stream_url` | string | HLS clip URL |
| `player_url` | string | Web player URL |

### Delivery semantics & idempotency (docs-confirmed)

- **Webhook = at-least-once.** May deliver duplicates. **Respond 2xx fast,
  process async, dedupe.** Matches `architecture.md` (Redis idempotency).
- **`event_id`** is the documented dedupe field. The official idempotency
  recipe is `sha256(f"{event_id}:{timestamp}")` stored with TTL; this project
  uses Redis `SET key 1 NX EX 86400`.
- For the **lifecycle** envelope there is no `event_id` — dedupe on
  `(capture_session_id, event, timestamp)` instead.
- **Signature verification: ⚠️ NOT documented.** No `X-VideoDB-Signature`
  header, signing secret, or SDK verifier exists in the SDK source or the
  reviewed docs. See Gaps. Treat the ngrok URL as the trust boundary +
  rely on `event_id` idempotency; do not promise HMAC verification.

---

## 10. WebSocket event schema ✅ (connection) / 🟡 (frame shapes)

```python
# Connection.connect_websocket(collection_id="default") -> WebSocketConnection
ws_wrapper = conn.connect_websocket()         # GET /collection/{cid}/websocket
ws = await ws_wrapper.connect()               # first frame carries connection_id
ws.connection_id                               # pass into index_*/start_transcript/create_alert

async for frame in ws.receive():               # async generator of dict
    ch = frame.get("channel")
    ...
# ws.send(dict) and `async with WebSocketConnection(url) as ws:` also supported.
```

> SDK method is `ws.receive()` (async generator). Some docs show `ws.stream()`
> — that alias is **not** in the SDK source; use `ws.receive()`.

WS channels: `capture_session` (lifecycle/status), `transcript`,
`scene_index` / `visual_index`, `audio_index`, `alert`.
**WebSocket = best-effort / at-most-once** (may miss events on disconnect;
truth lives in the webhook path — this is the project's dual-delivery rationale).

Frame shapes (docs):
```json
{ "channel": "transcript", "rtstream_id": "rts-xxx", "rtstream_name": "mic:default",
  "data": { "text": "...", "is_final": true, "start": 1710000001234, "end": 1710000002345 } }

{ "channel": "visual_index", "rtstream_id": "rts-xxx", "rtstream_name": "display:1",
  "data": { "text": "User is viewing a Slack conversation ...", "start": 1710000012340, "end": 1710000018900 } }

{ "channel": "audio_index", "rtstream_id": "rts-xxx", "rtstream_name": "mic:default",
  "data": { "text": "Discussion about scheduling ...", "start": 1710000021500, "end": 1710000029200 } }

{ "channel": "alert", "rtstream_id": "rts-xxx",
  "data": { "label": "sensitive_content", "triggered": true, "confidence": 0.92,
            "start": 1710000045100, "end": 1710000047800 } }
```
Note: WS `start`/`end` are **milliseconds** (epoch); `generate_stream()`
expects **seconds**. Divide by 1000 when converting WS ts → playback window.
(Doc inconsistency: `scene_index` channel name in one table vs `visual_index`
in the frame example — treat both as the visuals channel.)

---

## 11. Reusable event / alert templates ✅

Events are **reusable detection templates** created once at the connection
level, then attached to any stream's scene index as an alert.

```python
# --- 1. Define reusable event templates once (Connection-level) ---
# Connection.create_event(event_prompt: str, label: str) -> str  # returns event_id
ev_modal   = conn.create_event(
    event_prompt="An unexpected modal dialog or popup appears over the app UI",
    label="unexpected_modal")
ev_spinner = conn.create_event(
    event_prompt="A loading spinner or progress indicator stays visible without resolving",
    label="stuck_spinner")
ev_auth    = conn.create_event(
    event_prompt="An authentication or login failure / invalid credentials error is shown",
    label="auth_failure")

# Connection.list_events() -> List[dict]   # GET /rtstream/event
templates = conn.list_events()

# --- 2. Attach a template to a stream's scene index per run (Alert) ---
# RTStreamSceneIndex.create_alert(event_id, callback_url, ws_connection_id=None) -> alert_id
alert_id = scene_index.create_alert(
    event_id=ev_auth,
    callback_url="https://<ngrok>/webhooks/videodb",
    ws_connection_id=ws.connection_id,     # optional dual delivery
)

# --- 3. Manage alerts ---
scene_index.list_alerts()                  # List[dict]  (alert_id, event_id, status)
scene_index.disable_alert(alert_id)
scene_index.enable_alert(alert_id)
```

- One `event-...` template is reusable across runs/streams: re-call
  `create_alert(event_id=<same id>, ...)` on each new run's `scene_index`.
- Raw REST: `POST /rtstream/event` `{event_prompt,label}` → `{event_id}`;
  `POST /rtstream/{stream_id}/index/{scene_index_id}/alert`
  `{event_id, callback_url, ws_connection_id}` → `{alert_id}`.
- ⚠️ `scene_index.delete_alert(alert_id)` appears in docs but is **not** in
  the SDK source (`RTStreamSceneIndex` has create/list/enable/disable only).

---

## 12. Copy-paste signature index

```python
# ---- auth / client ----
videodb.connect(api_key=None, session_token=None,
                base_url="https://api.videodb.io", log_level=logging.INFO, **kwargs) -> Connection
conn.get_collection(collection_id="default") -> Collection

# ---- capture session ----
conn.create_capture_session(end_user_id, collection_id="default",
    callback_url=None, ws_connection_id=None, metadata=None) -> CaptureSession
conn.generate_client_token(expires_in=86400) -> str
conn.get_capture_session(session_id, collection_id="default") -> CaptureSession
conn.list_capture_sessions(collection_id="default", status=None) -> list[CaptureSession]
CaptureSession.get_rtstream(category) -> List[RTStream]   # category: RTStreamChannelType.*
CaptureSession.displays -> List[VideoChannel]
CaptureSession.export(video_channel_id=None, ws_connection_id=None) -> dict

# ---- desktop capture client (async) ----
CaptureClient(client_token, base_url=None)
await CaptureClient.request_permission(kind)            # "microphone"|"screen_capture"
await CaptureClient.list_channels() -> Channels         # .mics .displays .system_audio .cameras (ChannelList; .default)
await CaptureClient.start_session(capture_session_id, channels, primary_video_channel_id=None)
await CaptureClient.stop_session()
await CaptureClient.shutdown()
async for ev in CaptureClient.events(): ...
channel.store: bool ; channel.is_primary: bool ; await channel.pause()/resume()

# ---- rtstream lifecycle / playback ----
coll.get_rtstream(id) -> RTStream
coll.list_rtstreams(limit=None, offset=None, status=None, name=None, ordering=None) -> List[RTStream]
RTStream.start() / RTStream.stop()
RTStream.generate_stream(start:int, end:int, player_config=None) -> str   # returns player_url; sets .stream_url
RTStream.get_embed_code(width="100%", height=405, title="VideoDB Player", allow_fullscreen=True) -> str
RTStream.export(name=None) -> RTStreamExportResult(video_id, stream_url, player_url, name, duration)
RTStream.get_transcript(page=1, page_size=100, start=None, end=None, since=None, engine=None) -> dict

# ---- indexing ----
RTStream.start_transcript(ws_connection_id=None, engine=None) -> dict
RTStream.stop_transcript(engine=None) -> dict
RTStream.index_visuals(prompt=None, batch_config=None, model_name=None,
    model_config={}, name=None, ws_connection_id=None) -> RTStreamSceneIndex
    #   batch_config = {"type":"time","value":<window_s>,"frame_count":<n>}
RTStream.index_audio(prompt=None, batch_config=None, model_name=None,
    model_config={}, name=None, ws_connection_id=None) -> RTStreamSceneIndex
    #   batch_config = {"type":"word"|"sentence"|"time","value":<int>}
RTStream.index_spoken_words(prompt=None, segmenter=Segmenter.word, length=10,
    model_name=None, model_config={}, name=None, ws_connection_id=None) -> RTStreamSceneIndex
RTStream.index_scenes(extraction_type=SceneExtractionType.time_based,
    extraction_config={"time":2,"frame_count":5}, prompt="Describe the scene",
    model_name=None, model_config={}, name=None, ws_connection_id=None) -> RTStreamSceneIndex
RTStream.list_scene_indexes() -> List[RTStreamSceneIndex]
RTStream.get_scene_index(index_id) -> RTStreamSceneIndex
RTStreamSceneIndex.start() / .stop()
RTStreamSceneIndex.get_scenes(start=None, end=None, page=1, page_size=100) -> {"scenes":[...], "next_page":bool}

# ---- search / compile ----
RTStream.search(query, index_id=None, result_threshold=None, score_threshold=None,
    dynamic_score_percentage=None, filter=None) -> RTStreamSearchResult
RTStreamSearchResult.get_shots() -> List[RTStreamShot]
RTStreamShot(.rtstream_id .start .end .text .search_score .scene_index_id .metadata)
RTStreamShot.generate_stream() -> str ; RTStreamShot.play() -> str
coll.search(query, search_type=SearchType.semantic, index_type=IndexType.spoken_word,
    result_threshold=None, score_threshold=None, dynamic_score_percentage=None) -> SearchResult
SearchResult.get_shots() -> List[Shot] ; SearchResult.compile() -> str ; SearchResult.play() -> str

# ---- events / alerts (reusable templates) ----
conn.create_event(event_prompt, label) -> str            # event_id
conn.list_events() -> List[dict]
RTStreamSceneIndex.create_alert(event_id, callback_url, ws_connection_id=None) -> str  # alert_id
RTStreamSceneIndex.list_alerts() -> List[dict]
RTStreamSceneIndex.enable_alert(alert_id) / .disable_alert(alert_id)

# ---- websocket ----
conn.connect_websocket(collection_id="default") -> WebSocketConnection
await WebSocketConnection.connect() -> WebSocketConnection   # sets .connection_id
async for frame in WebSocketConnection.receive(): ...        # dict frames
await WebSocketConnection.send(dict) ; await WebSocketConnection.close()

# ---- constants ----
from videodb import (SearchType, IndexType, SceneExtractionType, Segmenter,
                     RTStreamChannelType, MediaType, AuthenticationError, SearchError)
SearchType.semantic|keyword ; IndexType.spoken_word|scene
SceneExtractionType.shot_based="shot"|time_based="time"|transcript="transcript"
Segmenter.time|word|sentence ; RTStreamChannelType.mic|screen|system_audio
```

---

## Gaps / unverified (read before relying on these)

| # | Item | Status | Detail |
|---|---|---|---|
| 6 | Per-scene custom metadata | **GAP** | No SDK call attaches arbitrary `task_id`/`run_status`/`divergence_point` to live RTStream scene records. `Scene.metadata` exists only for the uploaded-Video path. Keep run metadata on `CaptureSession.metadata` + Supabase; correlate by ids+timestamps. |
| 9 | Webhook signature/verification | **GAP** | No signing header, secret, or SDK verifier documented anywhere in SDK source or reviewed docs. Trust boundary = the ngrok URL; dedupe by `event_id`. Do not claim HMAC verification. |
| 7 | Keyword search in a collection | **PARTIAL** | `KeywordSearch.search_inside_collection` raises `NotImplementedError`. Use RTStream semantic search (`rts.search`) — keyword/collection-scene search is not implemented in the SDK. |
| 6/7 | `search(filter=[...])` dict shape | **GAP** | `filter` is accepted but the metadata-filter object schema is undocumented in SDK + reviewed docs. |
| 10 | WS frame field exactness | **PARTIAL** | Connection/`receive()` is SDK-verified. Frame JSON is docs-only; docs are internally inconsistent (`scene_index` vs `visual_index` channel name; `ws.stream()` alias does not exist — use `ws.receive()`). WS `start/end` are ms; playback wants seconds. |
| 11 | `delete_alert` | **MINOR GAP** | Shown in docs, absent from SDK source. Only create/list/enable/disable are in the SDK. |
| 2 | `generate_client_token` response | **NOTE** | SDK returns only `.get("token")`. REST also returns `expires_at` (unix int) & `expires_in`; build the ISO `expires_at` for `/sessions/start` yourself. |
| 1 | Env var name | **NOTE** | Correct env var is `VIDEO_DB_API_KEY` (the MASTER/`api-contracts` `VIDEODB_API_KEY` is wrong). |

### Source URLs used
- SDK source (authoritative, `video-db/videodb-python@main`):
  `videodb/__init__.py`, `client.py`, `capture.py`, `capture_session.py`,
  `rtstream.py`, `search.py`, `collection.py`, `shot.py`, `scene.py`,
  `websocket_client.py`, `_constants.py`
  (`https://raw.githubusercontent.com/video-db/videodb-python/main/videodb/<file>.py`)
- https://docs.videodb.io/llms.txt (doc index)
- https://docs.videodb.io/api-reference/capture/create_session.md
- https://docs.videodb.io/api-reference/capture/create_session_token.md
- https://docs.videodb.io/api-reference/capture/start_session.md
- https://docs.videodb.io/api-reference/capture/get_session.md
- https://docs.videodb.io/api-reference/rtstream/events-alerts/create_event.md
- https://docs.videodb.io/api-reference/rtstream/events-alerts/create_alert.md
- https://docs.videodb.io/api-reference/rtstream/scene-indexing/search_rtstream.md
- https://docs.videodb.io/api-reference/rtstream/scene-indexing/create_rtstream_scene_index.md
- https://docs.videodb.io/api-reference/rtstream/get_rtstream_stream.md
- https://docs.videodb.io/pages/act/live-action/alerts-and-callbacks.md
- https://docs.videodb.io/pages/act/live-action/webhooks-and-reliability.md
- https://docs.videodb.io/pages/ingest/capture-sdks/realtime-context.md
- https://docs.videodb.io/pages/ingest/capture-sdks/overview
- https://github.com/video-db/videodb-capture-quickstart
</content>
</invoke>
