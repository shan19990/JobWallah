# Contributing to JobWallah

Thank you for your interest in contributing! All contributions are welcome, from bug reports to new scraper integrations.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/JobWallah.git
   cd JobWallah
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Follow the [local setup instructions](README.md#getting-started).

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/shan19990/JobWallah/issues) and include:
- A clear title and description
- Steps to reproduce the problem
- Expected vs. actual behaviour
- Python version, OS, and relevant dependency versions

### Suggesting Features

Open a GitHub Issue with the `enhancement` label. Describe the use-case and why it would benefit other users.

### Submitting a Pull Request

1. Make your changes in a focused, well-named branch.
2. Keep commits atomic — one logical change per commit.
3. Write a clear PR description explaining **what** changed and **why**.
4. Make sure the app runs without errors before submitting.
5. Reference related issues with `Closes #<issue-number>` in the PR description.

## Adding a New Job Portal Scraper

Each scraper lives in its own Django app under the project root:

```
new_portal/
├── __init__.py
├── apps.py
├── urls.py
├── views.py        ← scrape() view that returns JSON {"jobs": [...]}
├── models.py
└── migrations/
```

The scraper view must accept the query parameters `keywords`, `locations`, `wfh_types`, and `experience`, and return:

```json
{
  "jobs": [
    {
      "title": "...",
      "company": "...",
      "location": "...",
      "link": "..."
    }
  ]
}
```

Register the new app in `jobwallah/settings.py` and add its URL to `jobwallah/urls.py`.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use descriptive variable and function names.
- Do not commit credentials, `.env` files, or `chromedriver.exe` binaries.

## Security

If you discover a security vulnerability, please **do not** open a public issue. Email the maintainer directly instead.
