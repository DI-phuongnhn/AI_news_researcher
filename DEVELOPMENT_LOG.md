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

### 2026-03-18 (Final Cleanup & Refinement)
- **Stricter Noise Filtering**: Re-implemented `filter_relevance` in `main.py` using Regex word boundaries (`\b`) to avoid false positives (e.g., matching "ai" in Vietnamese words like "gái").
- **Noise Blacklist**: Added patterns to exclude entertainment news (Oscar, animation, movie) and common question phrases (help wanted, consultancy).
- **Data Verifiction**: Successfully purged 4 off-topic items from the live dashboard via a cleanup script.
- **Project Hygiene**: Removed all temporary processing and cleanup scripts from the `src/` directory to maintain a production-ready codebase.
- **UI Logic Finalization**: Confirmed grouping by Scan Date and ArXiv density limits (max 5) are working correctly on GitHub Pages.

### Phase 5: High-Capacity & Technical Depth Expansion
- **Source Expansion**: Multiplied search depth to target **20+ high-quality items** per day.
- **Social Integration**: Added explicit targeted searches for **X (Twitter), Facebook, and Reddit** discussions.
- **Multi-Key Rotation**: Upgraded the rotator to handle **Horizontal Scaling** (cycling through multiple API keys) and **Vertical Scaling** (cycling through model generations).
- **Data Persistence**: Moved away from daily overwrites to a **Historical Archive** (`all_news.json`).
- **Dashboard Upgrades**: Implemented **Pagination**, Group-by-Date rendering, and **Dynamic Hot Keywords** dựa trên dữ liệu thực tế.
- **Full Refactoring**: Redesigned the codebase for modularity, adding comprehensive **Vietnamese/English docstrings** and PEP 8 compliance.

---

## Key Technical Components

### 1. `src/agent/model_rotator.py` (`SmartRotator`)
The upgraded "brain" of the API layer. It maintains a singleton instance that tracks quota usage across a grid of API Keys and Model IDs. It ensures zero-downtime processing even when hitting Free Tier limits.

### 2. `src/fetcher/keyword_discovery.py`
Now specialized in identifying new Models (e.g., GPT-5, OpenClaw) and Frameworks, providing high-signal context for the news search.

### 3. `src/fetcher/search_fetcher.py`
Includes specialized query builders for Social Media platforms, using `site:` operators to find community-driven technical signals.

### 4. `src/agent/summarizer.py`
An AI-driven gatekeeper that evaluates technical depth and provides high-density Vietnamese summaries. It can process up to 45 candidates to ensure the 20-item quality quota is met.

### 5. `index.html` (Enhanced Dashboard)
A performant Vanilla JS frontend hỗ trợ phân trang, xem lại dữ liệu lịch sử và các badge keyword động ("Hot" status).

---

## Technical Debt & Future Work
- **Performance**: Khi `all_news.json` phình to, việc chuyển sang database (SQLite) hoặc tối ưu hóa load dữ liệu client-side sẽ là cần thiết.
- **Translation Fidelity**: Nghiên cứu các mô hình dịch chuyên sâu cho thuật ngữ AI chuyên ngành (vd: "Mixture-of-Experts").
- **Automated Verification**: Cài đặt unit tests để đảm bảo fetcher hoạt động ổn định trước thay đổi layout của các công cụ tìm kiếm.

---
*Updated: March 2026*
*Created by [Antigravity AI Agent] for [NguyenHaNhatPhuong]*
