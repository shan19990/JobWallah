<div align="center">

# JobWallah

**AI-powered job aggregator — search across Naukri, LinkedIn, Indeed & Glassdoor in one click**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5-412991?style=flat&logo=openai&logoColor=white)](https://openai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

**JobWallah** eliminates the frustration of switching between multiple job portals. Enter your skills, location, and experience once — and get aggregated results from **Naukri, LinkedIn, Indeed, and Glassdoor** simultaneously. An AI chatbot helps you refine your search, and the resume parser extracts your profile details automatically.

---

## Features

- **Multi-platform aggregation** — parallel scraping from Naukri, LinkedIn, Indeed, and Glassdoor using a thread pool
- **Smart filters** — filter by keyword/skills, location, experience (years), and job type (remote / hybrid / on-site)
- **AI chatbot** — GPT-3.5-powered assistant that understands natural-language job queries and returns structured search parameters
- **Resume parser** — upload a PDF or DOCX resume; GPT-3.5 extracts name, phone, email, location, experience, and skills automatically
- **Async task queue** — Redis + Django-Q for background scraping jobs

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Django 5.0 |
| AI / LLM | OpenAI GPT-3.5-turbo |
| Web scraping | Selenium 4, BeautifulSoup4, webdriver-manager |
| Resume parsing | PyMuPDF (PDF), python-docx (DOCX) |
| NLP | NLTK |
| Task queue | Redis, Django-Q |
| Production server | Gunicorn |
| Database | SQLite (dev) |

---

## Project Structure

```
JobWallah/
├── jobwallah/          # Django project config (settings, urls, wsgi, asgi)
├── website/            # Core app — index view, chatbot, resume upload
├── naukri/             # Naukri scraper app
├── linkedin/           # LinkedIn scraper app
├── indeed/             # Indeed scraper app
├── glassdoor/          # Glassdoor scraper app
├── templates/
│   ├── base/           # Base HTML templates
│   └── website/        # Frontend views
├── static/
│   └── resume/         # Temporary resume storage (cleared after processing)
├── logs/               # Application logs
├── manage.py
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Google Chrome (matching version for ChromeDriver)
- Redis server running locally (`redis-server`)
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the repository

```bash
git clone https://github.com/shan19990/JobWallah.git
cd JobWallah
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values (see [Configuration](#configuration) below).

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Start Redis (required for Django-Q task queue)

```bash
redis-server
```

### 7. Start the Django-Q cluster (in a separate terminal)

```bash
python manage.py qcluster
```

### 8. Run the development server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Configuration

Copy `.env.example` to `.env` and set the following variables:

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) | Yes |
| `DEBUG` | `True` for development, `False` for production | Yes |
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | Yes (prod) |
| `REDIS_URL` | Redis connection URL (default: `redis://localhost:6379/0`) | Yes |

---

## Usage

### Searching for jobs

1. Open the app in your browser.
2. Enter your desired **skill / keyword** (e.g. `Python Developer`).
3. (Optional) Add **location**, **years of experience**, and **job type**.
4. Select the **job portals** to search (Naukri, LinkedIn, Indeed, Glassdoor).
5. Click **Search** — results from all selected platforms appear in seconds.

### AI Chatbot

Type naturally in the chat box:

```
"Find me remote Python backend jobs in Bangalore with 2 years experience on LinkedIn and Naukri"
```

The chatbot extracts the parameters and triggers the search automatically.

### Resume Parser

1. Click **Upload Resume**.
2. Select a `.pdf` or `.docx` file.
3. JobWallah extracts your name, contact details, location, skills, and experience using GPT-3.5.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Homepage / job search UI |
| `POST` | `/` | Submit job search (returns JSON) |
| `POST` | `/upload-resume/` | Upload and parse a resume |
| `POST` | `/chat/` | Send a message to the AI chatbot |
| `GET` | `/naukri/scrape/` | Naukri scraper (internal) |
| `GET` | `/indeed/scrape/` | Indeed scraper (internal) |
| `GET` | `/linkedin/scrape/` | LinkedIn scraper (internal) |
| `GET` | `/glassdoor/scrape/` | Glassdoor scraper (internal) |

Query parameters for scraper endpoints: `keywords`, `locations`, `wfh_types`, `experience`

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Author

**Shankhanil Ghosh** — [GitHub](https://github.com/shan19990)
