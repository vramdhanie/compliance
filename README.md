# Compliance Q&A

[![License: MIT](https://img.shields.io/github/license/vramdhanie/compliance?color=green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![uv](https://img.shields.io/badge/packaging-uv-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Claude](https://img.shields.io/badge/LLM-Claude-D97757?logo=anthropic&logoColor=white)](https://docs.claude.com)

Answers vendor due-diligence and compliance questionnaires from a folder of
policy PDFs. Point it at a spreadsheet of questions and a directory of
policies; it writes the answers back into the spreadsheet, skipping anything
the documents don't cover.

Originally a MongoDB + chromadb + langchain RAG pipeline on Azure OpenAI
(hence the git history); rewritten in 2026 as a single script on the
Anthropic API. The whole corpus fits in Claude's context window, so there is
no retrieval step — the PDFs are sent whole and prompt-cached.

## How it works

- `pdfs/` holds the policy PDFs (gitignored — policy documents and
  questionnaires never enter the repo). Text is extracted with pypdf and
  concatenated into one corpus.
- The system instruction and the full corpus are sent as cached system blocks
  (`cache_control: ephemeral`), so the first question pays for the corpus
  once and every later question reuses the cache at a fraction of the cost.
- Each question in column A of the spreadsheet is asked one at a time;
  answers go in column B. Questions the documents don't answer (or that ask
  for an attachment) are left blank.
- The spreadsheet is saved after every answer, and rows that already have an
  answer are skipped on the next run — an interrupted run resumes by just
  re-running. Blank (skipped) rows are asked again.
- Answers that hit the token cap are retried once with a larger cap, then
  flagged `[TRUNCATED]` if still cut off.

## Usage

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

```bash
uv run main.py "Vendor Due Diligence Questionnaire.xlsx"          # PDFs from ./pdfs
uv run main.py questions.xlsx /path/to/policies                   # explicit PDF dir
```

Spreadsheet format: row 1 is a header; questions in column A from row 2.
Column B is overwritten with the answers.

## License

[MIT](LICENSE) © Vincent Ramdhanie
