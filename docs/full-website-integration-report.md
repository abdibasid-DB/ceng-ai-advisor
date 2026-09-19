# Stage 18 Full Website Integration Report

## Stage Objective

Stage 18 integrated the working Stage 17 chatbot into a complete website for the AI-Powered Computer Engineering Student Advisor university project. The goal was to preserve the working RAG chatbot while adding a professional website shell and supporting pages for project presentation and defense.

Development was migrated to:

```text
D:\Projects\ceng-ai-advisor
```

The migration was performed because the C: drive had very low free space. This was an environment/storage decision, not an application defect. The old C: project remains a backup.

## Website Architecture

The website remains a React + Vite frontend connected to the existing FastAPI backend:

```text
React + Vite
  -> FastAPI
  -> RAG pipeline
  -> ChromaDB
  -> Ollama
  -> qwen2.5:3b
```

The frontend communicates only with FastAPI. It does not call Ollama, ChromaDB, or any commercial LLM API directly.

## Routing And Navigation

Stage 18 uses lightweight state/hash-based navigation instead of adding React Router. This is sufficient for the five-section university project website and avoids an unnecessary dependency.

Implemented sections:

- `#home`
- `#advisor`
- `#computer-engineering`
- `#sources`
- `#about-project`

The shared navigation marks the active section with `aria-current="page"` and supports direct hash links.

## Shared Layout

`frontend/src/components/WebsiteLayout.jsx` provides:

- site header
- project identity
- primary navigation
- main content landmark
- footer

The layout is shared by all pages and keeps the chatbot visually consistent with the rest of the website.

## Home Page

`frontend/src/pages/HomePage.jsx` introduces the project and includes:

- project identity
- concise purpose
- "Ask the AI Advisor" primary action
- "View Knowledge Sources" secondary action
- source count summary
- topic areas users can ask about
- "How It Works" RAG explanation

The page does not hard-code chatbot answers.

## AI Advisor Page

`frontend/src/pages/AdvisorPage.jsx` preserves the Stage 17 chatbot in the integrated website. It keeps:

- current-session visible history
- example questions
- 500-character input limit
- empty/whitespace prevention
- Enter-to-send and Shift+Enter newline
- loading feedback
- duplicate-request prevention
- New Conversation
- readiness indicator
- citations
- source cards
- supporting evidence
- insufficient-information rendering
- out-of-scope rendering
- controlled network/backend error rendering

Visible frontend history remains browser-session UI state only. It does not mean the backend RAG pipeline has conversational memory.

## Computer Engineering Page

`frontend/src/pages/ComputerEngineeringPage.jsx` gives a concise, source-aware overview of Computer Engineering. Sections cover:

- what the field studies
- core learning areas
- programming and software development
- mathematics and foundations
- hardware/software and systems themes
- AI, cybersecurity, and future technologies
- career possibilities

The page avoids unsupported university-specific claims and points to relevant project source categories.

## Sources Page

`frontend/src/pages/SourcesPage.jsx` loads approved source metadata dynamically from FastAPI. It includes:

- approved source count
- search by title, organization, category, or type
- category filter
- source-type filter
- title
- organization/source name
- source type
- category
- language
- publication date with graceful "Not specified" display
- external source links
- controlled error display if the source API fails

The 56 sources are not duplicated manually in React.

## Source Metadata API

Stage 18 added:

```text
GET /api/v1/sources
```

Implementation files:

- `backend/app/api/sources.py`
- `backend/app/models/sources.py`

The endpoint reads from:

```text
knowledge_base/sources.json
```

Safe fields exposed:

- `source_id`
- `title`
- `source_name`
- `source_type`
- `url`
- `publication_date`
- `category`
- `language`

Internal fields are not exposed, including:

- `raw_file_path`
- `processed_file_path`
- local Windows paths
- acquisition notes and internal metadata

Expected approved source count: 56.

## About Project Page

`frontend/src/pages/AboutProjectPage.jsx` explains:

- project purpose
- why RAG is used
- curated knowledge base
- source-grounded answers
- local AI model
- technology stack
- project limitations

Correct stack shown:

- Frontend: React + Vite
- Backend: FastAPI
- Vector database: ChromaDB
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- LLM: `qwen2.5:3b`
- Runtime: Ollama

## Local AI Explanation

The website explains that the project is designed to perform LLM inference locally through Ollama using `qwen2.5:3b` rather than a commercial cloud LLM API. It does not claim absolute privacy or security guarantees.

## Limitations

The website states limitations clearly:

- answers depend on available knowledge-base evidence
- unsupported questions may return insufficient information or out-of-scope responses
- the advisor focuses on Computer Engineering
- local generation may take several seconds
- visible frontend history is not backend conversational memory

## Responsive Behavior

The integrated CSS supports desktop, tablet-style, and mobile-style widths:

- navigation wraps and becomes a two-column grid on narrow screens
- home sections collapse cleanly
- information cards become single-column
- source cards become single-column
- chatbot input and send button stack on mobile
- source links become full-width touch targets

## Accessibility

Implemented accessibility basics include:

- semantic header, nav, main, and footer landmarks
- page-level headings
- labeled question textarea
- labeled source filters
- `aria-current` active navigation
- `aria-live` readiness/loading/source-list updates
- visible focus styles for links, buttons, inputs, selects, textarea, and details summaries
- external link text includes hidden "opens in a new tab" context

## Chatbot Regression

The integrated AI Advisor page was validated with the required questions:

1. `What is Computer Engineering?`
   - Expected behavior: answered response with citations, source card, and supporting evidence.

2. `What courses are taught in Computer Engineering?`
   - Expected behavior: curriculum answer with `[S1]`, `[S2]`, `[S3]`-style citations and supporting course evidence.

3. `What is the best chocolate cake recipe?`
   - Expected behavior: out-of-scope response with no fabricated general advisor answer.

New Conversation, loading feedback, readiness, and duplicate-request prevention remain part of the integrated chatbot.

## Backend Regression

Backend tests passed after Stage 18 source API work and again after migration to D::

```text
tests.test_api: 16 passed
tests.test_rag_pipeline tests.test_retriever tests.test_llm_service: 46 passed
```

The source endpoint tests verify:

- HTTP 200 success
- safe fields exist
- internal paths are not returned
- source count matches the approved registry
- missing registry failure is controlled

## Frontend Build

The frontend production build passes from:

```text
D:\Projects\ceng-ai-advisor\frontend
```

using the bundled pnpm runtime:

```powershell
pnpm run build
```

## Integrated Test

The integrated application is run from D: with:

- Ollama running locally
- FastAPI at `http://127.0.0.1:8000`
- React/Vite at `http://localhost:5173`
- Swagger at `http://127.0.0.1:8000/docs`

Browser validation covers all five sections, navigation, sources search/filtering, readiness, and chatbot regression.

## Protected AI Artifacts

Stage 18 did not rebuild or modify:

- `knowledge_base/raw/`
- `knowledge_base/processed/`
- `knowledge_base/chunks/`
- `knowledge_base/embeddings/`
- `knowledge_base/vector_store/chroma/`

It also did not change:

- embedding model
- retrieval thresholds
- citation validation
- `qwen2.5:3b`
- Ollama architecture

## Remaining Work

Before final university submission, later stages may still need:

- final university project report
- 70-day daily diary
- defense slides
- defense script
- final manual review in the presentation environment
