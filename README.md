# FDD-WE6 · Agentic AI — participant notebooks

Public copies of the weekend's hands-on notebooks. Everything here is meant to be opened in
**Google Colab**; nothing needs to be installed locally and nothing here needs a GitHub account.

| # | Notebook | What you build | Open |
|---|---|---|---|
| 03 | `03_agentic_ai_sweng/03_scoutai_workshop_student.ipynb` | ScoutAI — the same competitor brief eight times, one agentic concept at a time: tools, RAG, skills, memory, LangGraph, MCP, A2A. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eth-fdd-fs26/FDD-WE6-public/blob/main/03_agentic_ai_sweng/03_scoutai_workshop_student.ipynb) |
| 04 | `04_langchain_betting/04_langchain_agents_student.ipynb` | A betting desk for a sport nobody has ever played — LangChain agents, an MCP server you write yourself, and the tools/harness/prompt dials that decide what an agent actually does. | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eth-fdd-fs26/FDD-WE6-public/blob/main/04_langchain_betting/04_langchain_agents_student.ipynb) |

## What you need

**An OpenRouter API key.** Get one at <https://openrouter.ai/keys>, then in Colab open the
**Secrets** panel (🔑 in the left sidebar), add a secret named `OPENROUTER_API_KEY`, and toggle
*Notebook access* on. Both notebooks check the key early and stop if it is missing.

## About `04_langchain_betting/exercise/`

Notebook 04 ships with a small package it clones from this repo on its first cell:

- `galactic/` — the Galactic Premier League: the sport, the two websites the notebook embeds,
  the agent's toolbox and the betting desk.
- `lc_viz.py` — the diagrams and quizzes.
- `mcp_servers/` — a ready-made MCP server to connect to. The second one is the one **you**
  write, in Task 2; the notebook saves it here when you run that cell.

Neither `galactic/` nor `lc_viz.py` is worth reading before the session — between them they
hold the quiz answers and the sport, and reading them costs you most of the exercise.
