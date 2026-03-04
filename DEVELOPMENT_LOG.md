# AI Technical News Researcher - Development Log

This document summarizes the development journey, architectural decisions, and technical evolution of the AI News Research Agent. It is intended for developers who want to understand the project's internal logic and history.

## project Objective
Create a fully automated agent that:
1.  Discovers trending AI technical topics across global communities (X, Reddit, Blogs).
2.  Fetches deep-dive technical content using English keywords to ensure quality.
3.  Summarizes finding in professional Vietnamese for a local tech audience.
4.  Excludes general news/PR fluff to maintain a "Senior Developer" level of signal.
5.  Optimizes for Google Gemini Free Tier quotas.

---

## Architectural Evolution

### Phase 1: Core Foundation (The Flask Era)
- **Initial Idea**: A Python script running locally that fetched RSS feeds and used Gemini to summarize them.
- **Frontend**: A Flask server provided the dashboard.
- **Problem**: Required the user to keep a terminal open to view the results.

### Phase 2: Refinement & Data Density
- **English-to-Vietnamese Strategy**: We realized that searching in Vietnamese directly produced shallow results. We shifted to discovering keywords in English/Japanese/Vietnamese, then using the **English keywords** to perform a "global search" to find high-density papers and blogs before translating the summary back to Vietnamese.
- **Strict Filtering**: Implemented an exclusion list for general news sites (VnExpress, CNN, etc.) to ensure only technical sources were processed.

### Phase 3: Quota Resilience (Model Rotation v1)
- **Challenge**: The Gemini Free Tier has strict daily limits.
- **Solution**: Developed the `ModelRotator` utility to switch models on `429` errors.

### Phase 4: Zero-Maintenance Hosting (Static Migration)
- **Transition**: Migrated from Flask to a **Static Dashboard** (`index.html`).
- **Logic**: The script saves to `data/latest_news.json`, rendered by Vanilla JS.
- **Deployment**: Hosted on **GitHub Pages**. Automation via **GitHub Actions** (8:00 AM VN Time) pushes both data and UI updates simultaneously.
- **Authentication**: Uses a **Personal Access Token (PAT)** to bypass 403 permission errors during the push step from GitHub Actions.
- **Refinement**: Some model names in the pool were outdated or required different identifiers. 
- **Validation**: Updated the fallback list to use verified identifiers (`gemini-flash-lite-latest`, etc.).
- **Error Handling**: Broadened detection to catch `REMITTER_LIMIT` and `RATE_LIMIT` strings, ensuring the bot never stops until all options are exhausted.

---

## Key Technical Components

### 1. `src/agent/model_rotator.py`
The "brain" of the API layer. It manages the pool of models and handles retries with a circular rotation logic. This maximizes the utilization of the Free Tier.

### 2. `src/fetcher/keyword_discovery.py`
Aggregates signal from social media and authoritative blogs to generate a tri-lingual tag cloud (English, Vietnamese, Japanese).

### 3. `src/fetcher/search_fetcher.py`
Uses `duckduckgo_search` with targeted English keywords to find the most recent technical deep-dives, bypassing generic news sites.

### 4. `index.html` (The Static Dashboard)
A minimalist, high-performance dashboard that parses the `latest_news.json`. It includes tag-based filtering and search, all without a backend server.

---

## Technical Debt & Future Work
- **X/Twitter API**: Currently uses conceptual aggregation; direct API integration would provide more real-time signals but requires a paid tier.
- **Database**: Currently uses JSON for simplicity. If the archive grows beyond 1,000 items, a lightweight DB (like SQLite) or a more robust JSON indexing might be needed.
- **Image Generation**: Future versions could use Imagen to generate unique header images for each daily report.

---
*Created by [Antigravity AI Agent] for [NguyenHaNhatPhuong]*
