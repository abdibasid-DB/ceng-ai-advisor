# Stage 17 Frontend Chatbot Integration Report

## Objective

Stage 17 added and validated a React/Vite chatbot frontend for the AI-Powered Computer Engineering Student Advisor. The frontend communicates with the approved FastAPI backend only:

```text
React -> FastAPI -> RAG -> ChromaDB -> Ollama/qwen2.5:3b
```

The frontend does not call Ollama, ChromaDB, or any commercial LLM API directly.

## Frontend Architecture

- Framework: React with Vite.
- Main page: `frontend/src/App.jsx`.
- Styling: `frontend/src/App.css`.
- Constants: `frontend/src/constants.js`.
- Centralized API service: `frontend/src/services/api.js`.

The API base URL defaults to:

```text
http://127.0.0.1:8000
```

It can be overridden with `VITE_API_BASE_URL`. The service calls:

- `POST /api/v1/chat`
- `GET /api/v1/readiness`

## Components

- `ChatInput.jsx`: textarea, 500-character limit, Enter-to-send, Shift+Enter newline, disabled states.
- `ChatMessage.jsx`: user/assistant message rendering, status labels, answer rendering, source panel.
- `SourceCard.jsx`: source title, organization, category, section headings, URL, evidence labels, supporting passages, technical chunk details.
- `StatusIndicator.jsx`: readiness status and retry control.
- `LoadingMessage.jsx`: visible loading feedback during request processing.

## Chat State And Behavior

The frontend stores visible message history in React state for the current browser session. Follow-up questions remain visible in the same conversation, but the backend RAG pipeline currently processes questions independently unless backend conversational memory is explicitly added later. Visible frontend conversation history does not mean the backend has conversational memory.

New Conversation clears the visible messages and input, then restores the welcome/example-question state.

Duplicate requests are prevented by disabling the input and Send button while a request is in flight and by ignoring submissions when `isLoading` is true.

## Rendering Behavior

Answered responses render the assistant answer text exactly as returned by FastAPI, preserving `[S1]`, `[S2]`, and related citation labels.

Source cards display:

- evidence labels
- source title
- source URL
- organization/source name
- category
- section headings
- supporting passages
- supporting chunk IDs under technical details

Supporting evidence is rendered in expandable details sections. The current implementation opens evidence details by default so evidence is immediately visible while remaining collapsible.

`insufficient_information` and `out_of_scope` responses are rendered as advisor status messages without normal source cards. Backend or network failures render a controlled service message.

## Readiness Indicator

The app checks `GET /api/v1/readiness` on load. It shows Ready when FastAPI, ChromaDB, and Ollama are available. It shows an unavailable/degraded state with a Retry control when the local backend or local RAG dependencies are unavailable.

## Responsive Design And Accessibility

The layout uses responsive CSS breakpoints for narrow screens. At mobile width, the hero actions stack, example questions become single-column, message width expands to the viewport, and the input/send controls stack vertically.

Basic accessibility checks:

- page title and chatbot section are exposed through headings/labels
- textarea has a visible label
- readiness updates use `aria-live`
- loading message uses `aria-live`
- source sections and example questions have accessible labels
- keyboard submission is supported with Enter
- Shift+Enter inserts a newline
- focus-visible styles are defined for buttons, links, textarea, and details summaries

## Dependency Installation And Build Validation

`npm` was not available on PATH in the validation shell, so the bundled pnpm runtime was used:

```powershell
pnpm
```

Pnpm initially needed network access to relink lockfile dependencies and then blocked the `esbuild` postinstall script. The minimal dependency fix was to approve the known required build script in `frontend/pnpm-workspace.yaml`:

```yaml
allowBuilds:
  esbuild: true
```

`pnpm rebuild esbuild` completed successfully. Production build validation passed:

```powershell
cd frontend
pnpm run build
```

Result:

```text
vite v7.3.6 building client environment for production...
36 modules transformed.
built successfully
```

## Development Server Validation

The Vite development server starts successfully with:

```powershell
cd frontend
pnpm run dev
```

Validated URL:

```text
http://localhost:5173/
```

## End-To-End Validation

FastAPI was started at:

```text
http://127.0.0.1:8000
```

Readiness returned:

- status: `ready`
- vector store available: true
- collection count: 792
- Ollama available: true
- model: `qwen2.5:3b`

Required questions tested through the real API and the browser UI:

1. `What is Computer Engineering?`
   - Result: `answered`
   - Citation labels visible: `[S1]`
   - Source card visible with URL and supporting evidence.

2. `What courses are taught in Computer Engineering?`
   - Result: `answered`
   - Citation labels visible: `[S1]`, `[S2]`, `[S3]`
   - Curriculum source card visible with URL and supporting evidence.

3. `What is the best chocolate cake recipe?`
   - Result: `out_of_scope`
   - No fabricated normal advisor answer was produced.

New Conversation was tested in the browser UI and cleared the visible conversation back to the welcome/example-question state.

## Backend Regression

Existing API regression tests passed:

```powershell
python -m unittest tests.test_api
```

Result:

```text
Ran 13 tests in 1.009s
OK
```

During validation, simultaneous first requests to readiness and chat exposed a backend initialization race in the shared RAG pipeline dependency. The minimal fix serializes first-time pipeline creation and reuses the same instance. This does not change retrieval thresholds, grounding rules, embeddings, vector-store data, Ollama configuration, or the API contract.

## Remaining Limitations

- Backend conversational memory is not implemented. Frontend history is visual/session-only.
- First supported query can be slow because the local embedding model and Ollama generation path may need to warm up.
- Visual validation was performed through browser accessibility state and functional interaction checks, not a full design QA screenshot suite.
- Broader website pages, final About/Sources pages, deployment, reports, diary, and slides remain out of scope for Stage 17.
