function SourceCard({ source, index, id }) {
  const score = source.best_similarity_score ?? source.similarity_score;
  const labels = source.evidence_labels?.filter(Boolean).join(", ");
  const passages = source.supporting_passages?.filter(Boolean) || [];
  const chunkIds = source.supporting_chunk_ids?.filter(Boolean) || [];

  return (
    <article className="source-card" id={id} tabIndex={-1}>
      <div className="source-card-header">
        <div>
          <span className="source-label">{labels || `Source ${index + 1}`}</span>
          <h4>{source.title || "Untitled source"}</h4>
        </div>
        {source.url ? (
          <a href={source.url} target="_blank" rel="noopener noreferrer">
            Open source
          </a>
        ) : null}
      </div>

      <dl className="source-meta">
        {source.publication_date ? <><dt>Published</dt><dd>{source.publication_date}</dd></> : null}
        <dt>Similarity score</dt>
        <dd>{typeof score === "number" && Number.isFinite(score) ? score.toFixed(3) : "Not available"}</dd>
        {source.source_name ? (
          <>
            <dt>Organization</dt>
            <dd>{source.source_name}</dd>
          </>
        ) : null}
        {source.category ? (
          <>
            <dt>Category</dt>
            <dd>{source.category.replaceAll("_", " ")}</dd>
          </>
        ) : null}
        {source.section_headings?.length ? (
          <>
            <dt>Section</dt>
            <dd>{source.section_headings.join(", ")}</dd>
          </>
        ) : null}
      </dl>

      {passages.length ? (
        <details className="evidence-details" open>
          <summary>View supporting evidence</summary>
          {passages.map((passage, passageIndex) => (
            <blockquote key={`${source.source_id || index}-${passageIndex}`}>{passage}</blockquote>
          ))}
        </details>
      ) : null}

      {chunkIds.length ? (
        <details className="technical-details">
          <summary>Technical details</summary>
          <p>Chunk IDs: {chunkIds.join(", ")}</p>
        </details>
      ) : null}
    </article>
  );
}

export default SourceCard;
