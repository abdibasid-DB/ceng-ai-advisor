# Knowledge Base Plan

## Purpose

The knowledge base will provide reliable, organized information for the AI-Powered Computer Engineering Student Advisor. Its purpose is to support answers about Computer Engineering education, academic expectations, career paths, skills, internships, graduate study, employment, future technologies, and common concerns of prospective students.

The final system will use Retrieval-Augmented Generation (RAG) with a locally deployed open-source LLM. This design stage does not implement retrieval, embeddings, ChromaDB, Ollama, or chatbot logic.

## Scope From University Example Questions

The `ceng-questions.pdf` document contains 60 representative questions. These questions define the expected scope of the knowledge base, but they must not be treated as fixed answers to memorize. The examples show that users may ask about:

- what Computer Engineering is
- curriculum and projects
- programming and mathematics requirements
- academic difficulty and student life
- careers, jobs, internships, salaries, and work abroad
- artificial intelligence, cybersecurity, and future technologies
- graduate study and specialization choices
- work-life balance and misconceptions

The guideline states that these examples are not the complete scope. Therefore, the knowledge base must also cover semantically related questions with different wording, synonyms, and different levels of detail.

## Need for Semantic Retrieval

The future RAG system must support semantic retrieval because prospective students may ask the same question in many different ways. For example, a user may ask whether AI will replace computer engineers, whether Computer Engineering is still worth studying, or whether the job market is future-proof. These questions may use different words but require overlapping source material.

Semantic retrieval will later allow the system to find relevant knowledge-base chunks by meaning, not only by exact keyword matching.

## Source Selection Criteria

Every source should be evaluated before it is added to the knowledge base. A useful source should be:

- reliable and traceable
- relevant to Computer Engineering
- recent enough for the topic
- written or published by a trustworthy institution, author, or organization
- useful for answering factual or advisory student questions
- not an unnecessary duplicate of an existing source
- suitable for later text cleaning, chunking, metadata preservation, and embedding

## Preference for Reliable and Recent Sources

The university guideline emphasizes reliable and up-to-date information. Sources from the last three to four years should be preferred whenever possible, especially for fast-changing topics such as artificial intelligence, cybersecurity, software engineering, employment trends, salaries, remote work, and future technologies.

Older sources may still be useful for stable topics, such as general definitions, degree structure, or foundational academic concepts, but they should include a note explaining why they are still acceptable.

## Preferred Source Types

Preferred sources include:

- official OSTIM Technical University Computer Engineering department pages
- official curriculum and course description documents
- academic articles and research papers
- professional engineering organizations
- educational websites and learning platforms
- career guidance resources
- industry reports and technology publications
- official documentation for programming languages, software development tools, AI, cybersecurity, cloud computing, and related fields

No fake references or invented URLs should be added. Internet sources will be collected in a later stage.

## Metadata Fields

Each source will be tracked in `knowledge_base/sources.json` using these fields:

- `source_id`: unique identifier for the source
- `title`: title of the document, page, report, article, or resource
- `source_name`: organization, website, institution, publisher, or document owner
- `source_type`: source category such as official page, curriculum document, academic paper, career resource, industry report, or official documentation
- `url`: original URL, if available
- `publication_date`: publication or last-updated date, when known
- `date_accessed`: date the source was collected or reviewed
- `category`: primary category from `knowledge_base/categories.json`
- `language`: language of the source
- `reliability_note`: reason the source is trusted, or limitations to remember
- `raw_file_path`: local path to the stored raw copy, when available
- `notes`: additional notes about scope, duplication, preprocessing, or useful sections

## Category Structure

The knowledge base will use these categories:

- Department Information
- Curriculum
- Programming
- Mathematics
- Student Life
- Career Opportunities
- Employment
- Salaries
- Artificial Intelligence
- Cybersecurity
- Internships
- Skills and Technologies
- Graduate Studies
- Specializations
- Future Technologies
- Remote Work
- Entrepreneurship
- Work-Life Balance
- Common Misconceptions

These categories cover the university example questions while leaving space for additional semantically related questions.

## Handling Duplicate and Outdated Sources Later

During source collection and preprocessing, duplicate sources will be detected by comparing titles, URLs, source names, and overlapping content. If two sources provide the same information, the more official, more recent, or more complete source should be preferred.

Outdated sources will be reviewed before use. If a source is outdated for a fast-changing topic, it should be replaced or marked with a caution in `reliability_note` or `notes`. Older sources may remain only when the information is still stable and useful.

## Preparing for Chunking and Embeddings Later

In a later stage, raw documents will be stored under `knowledge_base/raw/`. Processed text will be stored under `knowledge_base/processed/`.

Before embedding, each source should be cleaned and split into meaningful chunks. Chunk metadata should preserve the original `source_id`, title, category, source type, URL, date information, and reliability notes. This will allow future answers to show source/context information and make generated responses more explainable.

This stage only designs the knowledge-base structure and tracking system. It does not create embeddings or a vector database.
