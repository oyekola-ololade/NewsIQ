# Workflow Inventory

| File | Export name | Nodes | Evidence notes |
|---|---|---:|---|
| `01_scraper.json` | `NewsIQ_01_Scraper` | 12 | Ingestion, normalization, embeddings, semantic deduplication, database writes, logging |
| `02_research_agent.json` | `NewsIQ_02_Research_Agent` | 12 | Pending-headline query, web search, AI-assisted fact analysis, persistence, logging |
| `03_script_writer.json` | `NewsIQ_03_Script_Writer` | 19 | Daily and weekly branches, ranking, prompts, validation, script persistence |
| `04_video_generator.json` | `NewsIQ_04_Video_Generator` | 18 | TTS, composition service, video validation, Drive upload, approval email |
| `05_distribution.json` | `NewsIQ_05_Distribution_v2` | 31 | Daily/weekly branches, approval gate, publishing adapters, short-form extraction, notifications |

## Import notes

- Credential references are intentionally replaced with `REPLACE_IN_N8N`.
- Import does not equal successful execution.
- Configure and test one workflow at a time.
- Keep the distribution workflow inactive until a real approval mechanism and real publishing adapters exist.

