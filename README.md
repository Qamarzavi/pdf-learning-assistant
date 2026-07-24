# PDF Learning Assistant - Powered by Google Gemini AI 🚀

An AI-powered web application that transforms PDF documents into comprehensive learning materials using **Google Gemini API (FREE)**.

## ✨ Features

- 📄 **PDF Text Extraction** - Upload any PDF with selectable text
- 🤖 **AI Summary** - Get comprehensive summaries using Gemini AI
- 🔑 **Keywords** - Extract key terms and concepts automatically
- ❓ **Study Questions** - Generate important questions from content
- 📝 **Quiz Generator** - Auto-create MCQs with correct answers
- 📥 **PDF Reports** - Download all content as a professional PDF
- 👤 **User System** - Secure login, registration, and data management
- 💾 **History** - Save and revisit all your processed PDFs

## 🛠️ Tech Stack

| Category | Technology |
|----------|------------|
| **Backend** | Python Flask |
| **Database** | SQLite + SQLAlchemy |
| **AI** | Google Gemini-2.5-flash-lite API (FREE) |
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript |
| **PDF** | PyPDF2, ReportLab |
| **Auth** | Flask-Login |
| **Icons** | Font Awesome 6 |

## 📁 Project Structure
pdf-learning-assistant/
│
├── app.py # Main Flask application (routes, logic)
├── database.py # Database models & helper functions
├── requirements.txt # Python dependencies
├── .env # Environment variables (API keys)
├── .gitignore # Git ignore rules
├── README.md # Project documentation
│
├── uploads/ # Uploaded PDF storage
│
├── static/
│ ├── css/
│ │ └── style.css # Complete application styling
│ └── js/
│ └── script.js # Common JavaScript functions
│
├── templates/
│ ├── base.html # Base template (navbar, footer)
│ ├── login.html # Login page
│ ├── register.html # Registration page
│ ├── dashboard.html # User dashboard with stats
│ ├── upload.html # PDF upload with drag & drop
│ └── view.html # Results with 7 tabs
│
└── screenshots/ # Application screenshots
├── login.png
├── dashboard.png
├── upload.png
├── summary.png
├── quiz.png
└── flashcards.png
