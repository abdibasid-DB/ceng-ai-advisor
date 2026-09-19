import { useEffect, useMemo, useState } from "react";
import { getSources } from "../services/api.js";

function formatLabel(value) {
  return (value || "Unknown").replaceAll("_", " ");
}

function SourcesPage() {
  const [sourcesData, setSourcesData] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [sourceType, setSourceType] = useState("all");

  useEffect(() => {
    let ignore = false;

    async function loadSources() {
      setIsLoading(true);
      setError("");
      try {
        const data = await getSources();
        if (!ignore) {
          setSourcesData(data);
        }
      } catch (loadError) {
        if (!ignore) {
          setError(loadError?.message || "The approved source registry could not be loaded.");
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    loadSources();
    return () => {
      ignore = true;
    };
  }, []);

  const filteredSources = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return (sourcesData?.sources || []).filter((source) => {
      const matchesSearch =
        !normalizedSearch ||
        [source.title, source.source_name, source.category, source.source_type, source.url]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(normalizedSearch));
      const matchesCategory = category === "all" || source.category === category;
      const matchesType = sourceType === "all" || source.source_type === sourceType;
      return matchesSearch && matchesCategory && matchesType;
    });
  }, [sourcesData, search, category, sourceType]);

  return (
    <section className="page-section sources-page" aria-labelledby="sources-title">
      <p className="eyebrow">Knowledge Sources</p>
      <h1 id="sources-title">Sources And References</h1>
      <p className="page-intro">
        These references come from the approved project source registry. The website exposes public metadata only and
        avoids local file paths or internal processing details.
      </p>

      <section className="source-browser" aria-label="Source browser controls">
        <div className="source-browser-header">
          <div>
            <h2>Approved Registry</h2>
            <p>
              {isLoading
                ? "Loading approved source metadata..."
                : `${filteredSources.length} of ${sourcesData?.count || 0} registered sources shown; ${sourcesData?.indexed_count || 0} are indexed for RAG`}
            </p>
          </div>
        </div>

        <div className="filter-grid">
          <label>
            Search
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search title, organization, category..."
            />
          </label>

          <label>
            Category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="all">All categories</option>
              {(sourcesData?.categories || []).map((item) => (
                <option key={item} value={item}>
                  {formatLabel(item)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Source type
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              <option value="all">All source types</option>
              {(sourcesData?.source_types || []).map((item) => (
                <option key={item} value={item}>
                  {formatLabel(item)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error ? (
          <div className="inline-alert" role="alert">
            {error}
          </div>
        ) : null}

        {!isLoading && !error && filteredSources.length === 0 ? (
          <p className="empty-results">No sources match the current filters.</p>
        ) : null}

        <div className="registry-list" aria-live="polite">
          {filteredSources.map((source) => (
            <article className="registry-card" key={source.source_id}>
              <div>
                <span className="source-label">{source.source_id}</span>
                <h3>{source.title}</h3>
                <p>{source.source_name}</p>
                <p className={source.indexed_in_rag ? "index-status indexed" : "index-status registered-only"}>
                  {source.indexed_in_rag ? "Indexed in RAG knowledge base" : "Registered reference; not indexed in RAG"}
                </p>
              </div>
              <dl className="source-meta registry-meta">
                <dt>Publication / website</dt>
                <dd>{source.source_name || "Not specified"}</dd>
                <dt>Category</dt>
                <dd>{formatLabel(source.category)}</dd>
                <dt>Type</dt>
                <dd>{formatLabel(source.source_type)}</dd>
                <dt>Language</dt>
                <dd>{source.language || "Not specified"}</dd>
                <dt>Publication date</dt>
                <dd>{source.publication_date || "Not available"}</dd>
                <dt>Date added</dt>
                <dd>{source.date_added || "Not available"}</dd>
                <dt>URL / citation</dt>
                <dd>
                  {source.url ? (
                    <a className="citation-url" href={source.url} target="_blank" rel="noopener noreferrer">
                      {source.url}
                    </a>
                  ) : (
                    "No public URL or citation information listed"
                  )}
                </dd>
              </dl>
              {source.url ? (
                <a className="source-link" href={source.url} target="_blank" rel="noopener noreferrer">
                  Open source <span className="sr-only">(opens in a new tab)</span>
                </a>
              ) : (
                <p className="missing-url">No public URL listed</p>
              )}
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

export default SourcesPage;
