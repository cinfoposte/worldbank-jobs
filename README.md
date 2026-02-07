# World Bank Group Job Scraper

Automated RSS feed generator for job listings from the World Bank Group.

## RSS Feed URL
**Live Feed:** `https://cinfoposte.github.io/worldbank-jobs/worldbank_jobs.xml`

## About
This scraper automatically fetches job listings from [World Bank Group Careers](https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup) and generates an RSS 2.0 compliant feed that updates twice weekly.

## Features
- ✅ Scrapes JavaScript-rendered job listings using Selenium
- ✅ Generates W3C-valid RSS 2.0 feed
- ✅ Automated updates via GitHub Actions (Sundays & Wednesdays at 9:00 UTC)
- ✅ Publicly accessible via GitHub Pages
- ✅ No server required - runs entirely on GitHub infrastructure

## Update Schedule
The feed automatically updates:
- **Sundays** at 9:00 UTC
- **Wednesdays** at 9:00 UTC

## Job Information Included
Each job listing includes:
- Job title
- Direct link to application page
- Location
- Department (when available)

## Technical Details
- **Language:** Python 3.11
- **Scraping:** Selenium WebDriver with Chrome headless
- **Parsing:** BeautifulSoup4
- **Format:** RSS 2.0

## Local Usage

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser

### Installation
```bash
pip install -r requirements.txt
```

### Run Scraper
```bash
python worldbank_scraper.py
```

This generates `worldbank_jobs.xml` in the current directory.

## Validation
Validate the RSS feed at: https://validator.w3.org/feed/

## About World Bank Group
The World Bank Group works in every major area of development with a mission to end extreme poverty and promote shared prosperity.

---

**Created by:** cinfoposte
**GitHub:** https://github.com/cinfoposte/worldbank-jobs
**License:** MIT
