# RSS Feed Scraper — Setup Manual

A step-by-step guide for creating automated RSS feed scrapers that run on GitHub Actions and publish via GitHub Pages. Based on the working `worldbank-jobs` repository.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Structure](#repository-structure)
3. [Step 1: Create the GitHub Repository](#step-1-create-the-github-repository)
4. [Step 2: Create the Files](#step-2-create-the-files)
5. [Step 3: Configure GitHub Pages](#step-3-configure-github-pages)
6. [Step 4: Configure GitHub Actions Permissions](#step-4-configure-github-actions-permissions)
7. [Step 5: Push and Verify](#step-5-push-and-verify)
8. [Adapting for a New Organization](#adapting-for-a-new-organization)
9. [Secrets and Environment Variables](#secrets-and-environment-variables)
10. [Troubleshooting](#troubleshooting)
11. [File Contents Reference](#file-contents-reference)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                  GitHub Actions (cron)                    │
│  Runs on schedule → installs Chrome + Python deps        │
│  → runs scraper → commits XML → pushes to repo           │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│              Python Scraper (Selenium)                    │
│  Loads JS-rendered careers page → extracts job listings  │
│  → deduplicates against existing feed → generates RSS    │
└──────────────────┬───────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│              GitHub Pages (static hosting)                │
│  Serves the XML file at:                                 │
│  https://<user>.github.io/<repo>/<feed>.xml              │
└──────────────────────────────────────────────────────────┘
```

**How it works:**
1. GitHub Actions triggers on a cron schedule (e.g. twice a week).
2. The workflow installs Python, Chrome, and project dependencies.
3. The Python scraper uses Selenium (headless Chrome) to load the target careers page.
4. BeautifulSoup parses the rendered HTML and extracts job listings.
5. New jobs are compared against the existing XML feed to avoid duplicates.
6. An RSS 2.0 XML file is generated and committed back to the repository.
7. GitHub Pages serves the XML file as a public URL that any RSS reader can subscribe to.

**No secrets, API keys, or paid services are required.** Everything runs on free GitHub infrastructure.

---

## Repository Structure

```
<repo-name>/
├── .github/
│   └── workflows/
│       └── update-feed.yml          # GitHub Actions workflow (cron trigger)
├── .gitignore                       # Ignores Python artifacts, IDE files, logs
├── README.md                        # Project documentation
├── requirements.txt                 # Python dependencies
├── <org>_scraper.py                 # Main scraper script
└── <org>_jobs.xml                   # Generated RSS feed (created by scraper)
```

That's it — 5 files plus the generated XML output.

---

## Step 1: Create the GitHub Repository

1. Go to https://github.com/new
2. Create a new **public** repository (GitHub Pages requires public repos on free plans).
   - Name it descriptively, e.g. `worldbank-jobs`, `undp-jobs`, `who-jobs`.
3. Clone it locally:
   ```bash
   git clone https://github.com/<your-user>/<repo-name>.git
   cd <repo-name>
   ```

---

## Step 2: Create the Files

Create the following 5 files. The full contents of each file are in the [File Contents Reference](#file-contents-reference) section at the end.

### 2.1 `.gitignore`

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Selenium
chromedriver.log
geckodriver.log
selenium-debug.log

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
```

### 2.2 `requirements.txt`

```
selenium==4.16.0
webdriver-manager==4.0.1
beautifulsoup4==4.12.2
lxml==4.9.3
requests==2.31.0
```

### 2.3 `.github/workflows/update-feed.yml`

This is the automation engine. Replace the placeholder values marked with `<...>`.

```yaml
name: Update <ORG_NAME> Job Feed

on:
  schedule:
    # Cron expression — adjust to your needs
    # Examples:
    #   '0 9 * * 0,3'  = Sundays and Wednesdays at 9:00 UTC
    #   '0 8 * * 1-5'  = Weekdays at 8:00 UTC
    #   '0 6 * * *'    = Daily at 6:00 UTC
    - cron: '0 9 * * 0,3'
  workflow_dispatch:  # Allow manual triggering from the Actions tab

jobs:
  scrape-and-update:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Set up Chrome and ChromeDriver
      uses: browser-actions/setup-chrome@latest
      with:
        chrome-version: stable

    - name: Run scraper
      run: python <org>_scraper.py

    - name: Commit and push if changes
      run: |
        git config --local user.email "github-actions[bot]@users.noreply.github.com"
        git config --local user.name "github-actions[bot]"
        git add <org>_jobs.xml
        git diff --quiet && git diff --staged --quiet || (git commit -m "Update <ORG_NAME> job feed - $(date +'%Y-%m-%d %H:%M UTC')" && git push)
```

**Key points:**
- `browser-actions/setup-chrome@latest` installs both Chrome and ChromeDriver. No manual ChromeDriver management needed.
- The commit step only commits if the XML file actually changed.
- `workflow_dispatch` lets you trigger the workflow manually from the GitHub Actions tab for testing.

### 2.4 `<org>_scraper.py` — The Main Scraper

This is the core file. See the full template in the [File Contents Reference](#file-contents-reference) section.

The scraper has 5 functions:

| Function | Purpose |
|---|---|
| `setup_driver()` | Configures headless Chrome with Selenium |
| `generate_numeric_id(url)` | Creates a unique numeric GUID from a URL via MD5 |
| `get_existing_job_links(feed_file)` | Reads existing XML to track which jobs are already published |
| `scrape_<org>_jobs()` | Loads the careers page, extracts job data (title, link, location, department) |
| `generate_rss_feed(jobs, output_file)` | Builds the RSS 2.0 XML from the scraped data |
| `main()` | Orchestrates: load existing → scrape → deduplicate → generate feed |

### 2.5 `README.md`

```markdown
# <ORG_NAME> Job Scraper

Automated RSS feed generator for job listings from <ORG_NAME>.

## RSS Feed URL
**Live Feed:** `https://<your-user>.github.io/<repo-name>/<org>_jobs.xml`

## About
This scraper automatically fetches job listings from [<ORG_NAME> Careers](<CAREERS_URL>)
and generates an RSS 2.0 compliant feed that updates twice weekly.

## Features
- Scrapes JavaScript-rendered job listings using Selenium
- Generates W3C-valid RSS 2.0 feed
- Automated updates via GitHub Actions
- Publicly accessible via GitHub Pages
- No server required — runs entirely on GitHub infrastructure

## Update Schedule
The feed automatically updates per the cron schedule in
`.github/workflows/update-feed.yml`.

## Local Usage

### Prerequisites
- Python 3.8+
- Chrome/Chromium browser

### Installation
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### Run Scraper
\`\`\`bash
python <org>_scraper.py
\`\`\`

## Validation
Validate the RSS feed at: https://validator.w3.org/feed/
```

---

## Step 3: Configure GitHub Pages

1. Go to your repository on GitHub.
2. Navigate to **Settings** → **Pages**.
3. Under **Source**, select **Deploy from a branch**.
4. Select branch: **master** (or **main**), directory: **/ (root)**.
5. Click **Save**.
6. Wait 1–2 minutes for GitHub Pages to deploy.
7. Your feed will be available at:
   ```
   https://<your-user>.github.io/<repo-name>/<org>_jobs.xml
   ```

---

## Step 4: Configure GitHub Actions Permissions

For the workflow to commit and push the updated XML:

1. Go to your repository on GitHub.
2. Navigate to **Settings** → **Actions** → **General**.
3. Scroll to **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

Without this, the `git push` step in the workflow will fail with a permission error.

---

## Step 5: Push and Verify

```bash
# Add all files
git add .
git commit -m "Initial setup: RSS feed scraper"
git push origin master

# Trigger the workflow manually for a first test
# Go to: Actions tab → "Update <ORG_NAME> Job Feed" → "Run workflow"
```

After the workflow completes:
- Check the Actions tab for green checkmarks.
- Visit `https://<your-user>.github.io/<repo-name>/<org>_jobs.xml` to see the feed.
- Validate at https://validator.w3.org/feed/

---

## Adapting for a New Organization

To create a new RSS feed for a different organization, you need to change these values:

### Values to Replace

| Placeholder | Description | Example (World Bank) |
|---|---|---|
| `<ORG_NAME>` | Human-readable organization name | `World Bank Group` |
| `<org>` | Short lowercase identifier (used in filenames) | `worldbank` |
| `<CAREERS_URL>` | The organization's careers page URL | `https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup` |
| `<BASE_DOMAIN>` | The root domain of the careers site | `https://worldbankgroup.csod.com` |
| `<your-user>` | Your GitHub username or org | `cinfoposte` |
| `<repo-name>` | The GitHub repository name | `worldbank-jobs` |

### What to Customize in the Scraper

The part of the scraper that needs the most adaptation is the `scrape_<org>_jobs()` function. Different career sites have different HTML structures. You'll need to:

1. **Inspect the target careers page** — Open the page in Chrome, right-click → Inspect, and study the HTML structure of job listings.

2. **Adjust the element-finding strategies** — The current scraper uses 3 strategies in order:
   - Strategy 1: Find elements with CSS classes containing keywords like `job-card`, `job-item`, `position`, `vacancy`, `requisition`
   - Strategy 2: Find `<a>` tags with `requisition` in the href
   - Strategy 3: Find structured `<div>` or `<article>` elements containing a title and link

3. **Adjust the data extraction** — How title, link, location, and department are pulled from each element depends on the HTML structure.

4. **Adjust wait times** — Some sites load faster/slower. The `time.sleep(20)` may need to be adjusted.

5. **Test locally first** — Run `python <org>_scraper.py` locally to verify it finds jobs before pushing.

### Checklist for a New Feed

- [ ] Create new GitHub repository
- [ ] Copy all 5 files from this template
- [ ] Replace all placeholders in all files
- [ ] Inspect the target careers page HTML and adapt the scraper
- [ ] Test locally: `python <org>_scraper.py`
- [ ] Verify the generated XML is valid RSS
- [ ] Push to GitHub
- [ ] Enable GitHub Pages (Settings → Pages → Deploy from branch)
- [ ] Enable Actions write permissions (Settings → Actions → General)
- [ ] Trigger the workflow manually to test
- [ ] Verify the feed is accessible at the GitHub Pages URL
- [ ] Subscribe to the feed in an RSS reader to confirm it works

---

## Secrets and Environment Variables

**None required.** This setup uses:
- Public GitHub repository (free GitHub Pages)
- GitHub Actions (free for public repos)
- `browser-actions/setup-chrome` (installs Chrome/ChromeDriver in CI)
- No API keys, tokens, or paid services

The only "credential" is the built-in `GITHUB_TOKEN` that GitHub Actions provides automatically for commits. This requires the **read and write permissions** setting described in Step 4.

---

## Troubleshooting

### Workflow fails at "Run scraper"
- **ChromeDriver mismatch:** The `browser-actions/setup-chrome@latest` action should handle this. If not, try pinning a specific Chrome version.
- **Page structure changed:** The target site may have redesigned. Inspect the page and update the scraping strategies.
- **Timeout:** Increase `time.sleep(20)` if the page takes longer to load.

### Workflow fails at "Commit and push"
- **Permission denied:** Go to Settings → Actions → General → Workflow permissions → set to **Read and write permissions**.

### Feed shows 0 jobs
- The careers page may use a different HTML structure than expected. Run locally and add `print(soup.prettify()[:5000])` after the `soup = BeautifulSoup(...)` line to inspect what Selenium actually loaded.
- Some sites require additional scroll actions or clicking "Load more" buttons.

### GitHub Pages returns 404
- Ensure Pages is enabled (Settings → Pages).
- Ensure the XML file is committed to the branch that Pages is set to deploy from.
- Wait a few minutes after the first deploy.

### Feed not updating
- Check the Actions tab for failed runs.
- GitHub may disable scheduled workflows after 60 days of repo inactivity. Push a commit or trigger manually to re-enable.

---

## File Contents Reference

Below are the complete, copy-ready files with placeholders. Replace all `<...>` values.

### Complete Scraper Template: `<org>_scraper.py`

```python
#!/usr/bin/env python3
"""
<ORG_NAME> Job Scraper
Scrapes job listings from <ORG_NAME> careers site and generates an RSS feed
"""

import time
import os
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import hashlib
import html as html_module


def setup_driver():
    """Set up Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    chromedriver_path = shutil.which('chromedriver')
    if chromedriver_path:
        print(f"Using chromedriver at: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        print("Using chromedriver from system path")
        service = Service('chromedriver')

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def generate_numeric_id(url):
    """Generate unique numeric ID from URL"""
    hash_object = hashlib.md5(url.encode())
    hex_dig = hash_object.hexdigest()
    numeric_id = int(hex_dig[:16], 16) % 10000000000000000
    return str(numeric_id)


def get_existing_job_links(feed_file='<org>_jobs.xml'):
    """Extract job links from existing RSS feed"""
    existing_links = set()

    if not os.path.exists(feed_file):
        print("No existing feed found - all jobs will be considered new")
        return existing_links

    try:
        tree = ET.parse(feed_file)
        root = tree.getroot()

        for item in root.findall('.//item'):
            link_elem = item.find('link')
            if link_elem is not None and link_elem.text:
                existing_links.add(link_elem.text.strip())

        print(f"Found {len(existing_links)} existing jobs in previous feed")

    except Exception as e:
        print(f"Error reading existing feed: {str(e)}")
        print("Will treat all jobs as new")

    return existing_links


def scrape_jobs():
    """Scrape job listings from <ORG_NAME>"""
    # ─── CUSTOMIZE THIS URL ───
    url = "<CAREERS_URL>"

    print(f"Starting scraper for: {url}")
    driver = setup_driver()
    jobs = []

    try:
        driver.get(url)
        print("Page loaded, waiting for JavaScript to render...")

        wait = WebDriverWait(driver, 30)
        print("Waiting for job content to load...")
        time.sleep(20)  # Adjust based on page load speed

        # Scroll to trigger lazy-loading content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        job_elements = []

        # ─── STRATEGY 1: Find elements by CSS class keywords ───
        # Adjust these keywords based on the target site's HTML
        job_elements = soup.find_all(
            ['div', 'article', 'li'],
            class_=lambda x: x and any(
                keyword in str(x).lower()
                for keyword in ['job-card', 'job-item', 'position', 'vacancy', 'requisition']
            )
        )
        print(f"Strategy 1: Found {len(job_elements)} potential job elements")

        # ─── STRATEGY 2: Find links with job-related href patterns ───
        if not job_elements:
            job_links = soup.find_all(
                'a', href=lambda x: x and 'requisition' in str(x).lower()
            )
            job_elements = [link for link in job_links if len(link.get_text(strip=True)) > 5]
            print(f"Strategy 2: Found {len(job_elements)} job requisition links")

        # ─── STRATEGY 3: Find structured elements with title + link ───
        if not job_elements:
            for element in soup.find_all(['div', 'article']):
                title_elem = element.find(['h2', 'h3', 'h4', 'a'])
                link_elem = element.find('a', href=True)
                if title_elem and link_elem:
                    job_elements.append(element)
            print(f"Strategy 3: Found {len(job_elements)} structured elements")

        print(f"Processing {len(job_elements)} potential job listings...")

        for element in job_elements[:50]:
            try:
                job_data = {}

                # ─── Extract link ───
                if element.name == 'a' and element.get('href'):
                    href = element['href']
                    if href.startswith('http'):
                        job_data['link'] = href
                    elif href.startswith('/'):
                        job_data['link'] = f"<BASE_DOMAIN>{href}"
                    else:
                        job_data['link'] = f"<BASE_DOMAIN>/{href}"
                else:
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        href = link_elem['href']
                        if href.startswith('http'):
                            job_data['link'] = href
                        elif href.startswith('/'):
                            job_data['link'] = f"<BASE_DOMAIN>{href}"
                        else:
                            job_data['link'] = f"<BASE_DOMAIN>/{href}"
                    else:
                        continue

                # ─── Extract title ───
                if element.name == 'a':
                    job_data['title'] = element.get_text(strip=True)
                else:
                    title_elem = element.find(
                        ['h2', 'h3', 'h4', 'a'],
                        class_=lambda x: x and 'title' in str(x).lower()
                    )
                    if not title_elem:
                        title_elem = element.find(['h2', 'h3', 'h4'])
                    if not title_elem:
                        title_elem = element.find('a')
                    if title_elem:
                        job_data['title'] = title_elem.get_text(strip=True)
                    else:
                        job_data['title'] = element.get_text(strip=True)[:100]

                if not job_data.get('title') or len(job_data['title']) < 5:
                    continue

                # ─── Skip non-job links ───
                skip_keywords = ['search', 'filter', 'sort', 'login', 'sign in',
                                 'home', 'about', 'contact']
                if any(kw in job_data['title'].lower() for kw in skip_keywords):
                    continue

                # ─── Extract location ───
                location_elem = element.find(
                    ['span', 'div', 'p'],
                    class_=lambda x: x and 'location' in str(x).lower()
                )
                job_data['location'] = (
                    location_elem.get_text(strip=True) if location_elem
                    else "<DEFAULT_LOCATION>"
                )

                # ─── Extract department ───
                dept_elem = element.find(
                    ['span', 'div', 'p'],
                    class_=lambda x: x and 'department' in str(x).lower()
                )
                job_data['department'] = (
                    dept_elem.get_text(strip=True) if dept_elem else ""
                )

                # ─── Build description ───
                description_parts = []
                description_parts.append(
                    f"<ORG_NAME> has a vacancy for the position of {job_data['title']}"
                )
                if job_data.get('department'):
                    description_parts.append(f"in the {job_data['department']}")
                description_parts.append(f"Location: {job_data['location']}")
                job_data['description'] = " ".join(description_parts) + "."

                if job_data['title'] and job_data['link']:
                    jobs.append(job_data)
                    print(f"  [OK] {job_data['title']}")

            except Exception as e:
                print(f"  [ERROR] Error processing element: {str(e)}")
                continue

        print(f"\nSuccessfully scraped {len(jobs)} jobs")

    except Exception as e:
        print(f"Error during scraping: {str(e)}")

    finally:
        driver.quit()

    return jobs


def generate_rss_feed(jobs, output_file='<org>_jobs.xml'):
    """Generate RSS 2.0 feed from job listings"""

    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    rss.set('xml:base', '<BASE_DOMAIN>/')

    channel = ET.SubElement(rss, 'channel')

    title = ET.SubElement(channel, 'title')
    title.text = '<ORG_NAME> Job Vacancies'

    link = ET.SubElement(channel, 'link')
    link.text = '<BASE_DOMAIN>/'

    description = ET.SubElement(channel, 'description')
    description.text = 'List of vacancies at <ORG_NAME>'

    language = ET.SubElement(channel, 'language')
    language.text = 'en'

    atom_link = ET.SubElement(channel, 'atom:link')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')
    atom_link.set('href', 'https://<your-user>.github.io/<repo-name>/<org>_jobs.xml')

    pub_date = ET.SubElement(channel, 'pubDate')
    current_time = datetime.now(timezone.utc)
    pub_date.text = format_datetime(current_time)

    for job in jobs:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        item_title.text = job.get('title', 'Untitled Position')

        item_link = ET.SubElement(item, 'link')
        item_link.text = job.get('link', '')

        item_description = ET.SubElement(item, 'description')
        item_description.text = job.get('description', '')

        guid = ET.SubElement(item, 'guid')
        guid.set('isPermaLink', 'false')
        guid.text = generate_numeric_id(job.get('link', ''))

        item_pub_date = ET.SubElement(item, 'pubDate')
        item_pub_date.text = format_datetime(current_time)

        source = ET.SubElement(item, 'source')
        source.set('url', '<BASE_DOMAIN>/')
        source.text = '<ORG_NAME> Job Vacancies'

    xml_string = ET.tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_string)

    # Wrap descriptions in CDATA for safe HTML handling
    for item_node in dom.getElementsByTagName('item'):
        for desc_node in item_node.getElementsByTagName('description'):
            text_content = desc_node.firstChild.nodeValue if desc_node.firstChild else ''
            html_safe = html_module.escape(text_content, quote=False)
            while desc_node.firstChild:
                desc_node.removeChild(desc_node.firstChild)
            cdata = dom.createCDATASection(html_safe)
            desc_node.appendChild(cdata)

    pretty_xml = dom.toprettyxml(indent='  ')
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"\n[SUCCESS] RSS feed generated: {output_file}")
    print(f"  Total jobs in feed: {len(jobs)}")


def main():
    """Main execution function"""
    print("=" * 60)
    print("<ORG_NAME> Job Scraper")
    print("=" * 60)

    existing_links = get_existing_job_links()
    all_jobs = scrape_jobs()
    new_jobs = [job for job in all_jobs if job.get('link') not in existing_links]

    print("\n" + "=" * 60)
    print(f"Total jobs found: {len(all_jobs)}")
    print(f"New jobs (not in previous feed): {len(new_jobs)}")
    print(f"Existing jobs (skipped): {len(all_jobs) - len(new_jobs)}")
    print("=" * 60)

    if new_jobs:
        generate_rss_feed(new_jobs)
        print("\n[SUCCESS] Feed updated with new jobs!")

        print("\nNew jobs added to feed:")
        for i, job in enumerate(new_jobs, 1):
            print(f"  {i}. {job['title']}")
    else:
        print("\n[INFO] No new jobs found - feed not updated")
        if not os.path.exists('<org>_jobs.xml'):
            print("[INFO] Creating empty feed file")
            generate_rss_feed([])

    print("=" * 60)


if __name__ == "__main__":
    main()
```

### Complete Workflow Template: `.github/workflows/update-feed.yml`

```yaml
name: Update <ORG_NAME> Job Feed

on:
  schedule:
    - cron: '0 9 * * 0,3'
  workflow_dispatch:

jobs:
  scrape-and-update:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Set up Chrome and ChromeDriver
      uses: browser-actions/setup-chrome@latest
      with:
        chrome-version: stable

    - name: Run scraper
      run: python <org>_scraper.py

    - name: Commit and push if changes
      run: |
        git config --local user.email "github-actions[bot]@users.noreply.github.com"
        git config --local user.name "github-actions[bot]"
        git add <org>_jobs.xml
        git diff --quiet && git diff --staged --quiet || (git commit -m "Update <ORG_NAME> job feed - $(date +'%Y-%m-%d %H:%M UTC')" && git push)
```

### Quick-Reference: World Bank Example Values

For the working `worldbank-jobs` repository, the placeholders resolve to:

| Placeholder | Value |
|---|---|
| `<ORG_NAME>` | `World Bank Group` |
| `<org>` | `worldbank` |
| `<CAREERS_URL>` | `https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup` |
| `<BASE_DOMAIN>` | `https://worldbankgroup.csod.com` |
| `<DEFAULT_LOCATION>` | `Washington, DC` |
| `<your-user>` | `cinfoposte` |
| `<repo-name>` | `worldbank-jobs` |
