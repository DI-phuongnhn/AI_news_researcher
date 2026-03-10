# AI News Researcher

Một hệ thống tự trị chuyên nghiên cứu và tổng hợp tin tức AI kỹ thuật chuyên sâu từ đa nguồn (ArXiv, RSS, Reddit, X, Facebook) và hiển thị trên Dashboard tương tác.

## 🚀 Tính năng vượt trội

- **Tự động hóa hoàn toàn**: Tự động tìm kiếm từ khóa xu hướng, quét tin tức và tóm tắt chuyên sâu mỗi ngày.
- **Xoay vòng API thông minh**: Tận dụng tối đa Free Tier của Gemini bằng cơ chế xoay vòng nhiều API Key và nhiều Model khác nhau (Flash 2.0, Pro, Lite).
- **Phân tích kỹ thuật chuyên sâu**: Bộ lọc AI chỉ giữ lại các bài viết có giá trị học thuật/kỹ thuật cao (Kiến trúc mô hình, thuật toán mới, Agentic Frameworks).
- **Đa nguồn tin**: Tích hợp từ Google Search, RSS Feeds, Reddit (r/MachineLearning), X (Twitter), và Facebook.
- **Dashboard hiện đại**: Giao diện hiển thị tin tức được phân loại theo ngày, hỗ trợ phân trang và tìm kiếm theo Keyword.
- **Tóm tắt Tiếng Việt**: Cung cấp tóm tắt kỹ thuật cô đọng bằng Tiếng Việt cho các bài nghiên cứu quốc tế.

## 🛠️ Công nghệ sử dụng

- **Ngôn ngữ**: Python 3.10+
- **AI Engine**: Google Gemini API (GenAI SDK)
- **Data Fetching**: Feedparser, DuckDuckGo Search, Requests, BeautifulSoup4
- **Frontend**: HTML5, Vanilla CSS, JavaScript (Static Site)
- **CI/CD**: GitHub Actions (Tự động chạy hàng ngày)

## 📂 Cấu trúc dự án

```text
AI_news_researcher/
├── src/
│   ├── agent/
│   │   ├── model_rotator.py   # Xoay vòng Key/Model thông minh
│   │   └── summarizer.py      # Lọc và tóm tắt nội dung kỹ thuật
│   ├── fetcher/
│   │   ├── keyword_discovery.py # Khám phá xu hướng AI
│   │   ├── rss_fetcher.py       # Lấy tin từ arXiv, IEEE, v.v.
│   │   ├── reddit_fetcher.py    # Lấy tin từ Reddit
│   │   └── search_fetcher.py    # Tìm kiếm Google/Social Media
│   ├── config.py              # Cấu hình tập trung
│   └── main.py                # Entry point vận hành pipeline
├── data/
│   ├── latest_news.json       # Kết quả chạy mới nhất
│   └── all_news.json          # Lưu trữ lịch sử (Historical data)
├── index.html                 # Dashboard UI
└── .env                       # Chứa GEMINI_API_KEYS (Không push lên Git)
```

## ⚙️ Hướng dẫn cài đặt

1. **Clone dự án**:
   ```bash
   git clone https://github.com/DI-phuongnhn/AI_news_researcher.git
   cd AI_news_researcher
   ```

2. **Cài đặt thư viện**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình API Key**:
   Tạo file `.env` ở thư mục gốc và thêm các key của bạn (phân cách bằng dấu phẩy):
   ```env
   GEMINI_API_KEYS=key1,key2,key3
   ```

4. **Chạy hệ thống**:
   ```bash
   python src/main.py
   ```

5. **Xem Dashboard**:
   Mở file `index.html` bằng trình duyệt hoặc host trên GitHub Pages.

## 📈 Lịch sử phiên bản

- **v1.0**: Khởi tạo hệ thống tóm tắt RSS.
- **v2.0**: Thêm cơ chế xoay vòng Key & Model.
- **v3.0**: Mở rộng nguồn Social Media (X, Reddit, FB) & Phân trang Dashboard & Refactor code hoàn chỉnh.

---
*Phát triển bởi Antigravity Agent.*
