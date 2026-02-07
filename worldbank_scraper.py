#!/usr/bin/env python3
"""
World Bank Group Job Scraper
Scrapes job listings from World Bank Group careers site and generates an RSS feed
"""

import time
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom

def setup_driver():
    """Set up Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_worldbank_jobs():
    """Scrape job listings from World Bank Group"""
    url = "https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup"

    print(f"Starting scraper for: {url}")
    driver = setup_driver()
    jobs = []

    try:
        driver.get(url)
        print("Page loaded, waiting for JavaScript to render...")

        # Wait for job listings to load
        wait = WebDriverWait(driver, 30)
        print("Waiting for job content to load...")
        time.sleep(20)  # Give extra time for Cornerstone platform to load

        # Scroll to trigger lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        # Get page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # Try multiple strategies to find job listings
        job_elements = []

        # Strategy 1: Look for job card elements
        job_elements = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['job-card', 'job-item', 'position', 'vacancy', 'requisition']
        ))
        print(f"Strategy 1: Found {len(job_elements)} potential job elements")

        # Strategy 2: Look for links with requisition in href (actual job postings)
        if not job_elements:
            job_links = soup.find_all('a', href=lambda x: x and 'requisition' in str(x).lower())
            job_elements = [link for link in job_links if len(link.get_text(strip=True)) > 5]
            print(f"Strategy 2: Found {len(job_elements)} job requisition links")

        # Strategy 3: Look for any structured content with titles
        if not job_elements:
            for element in soup.find_all(['div', 'article']):
                title_elem = element.find(['h2', 'h3', 'h4', 'a'])
                link_elem = element.find('a', href=True)
                if title_elem and link_elem:
                    job_elements.append(element)
            print(f"Strategy 3: Found {len(job_elements)} structured elements")

        print(f"Processing {len(job_elements)} potential job listings...")

        for element in job_elements[:50]:  # Limit to first 50
            try:
                job_data = {}

                # Get job link
                if element.name == 'a' and element.get('href'):
                    href = element['href']
                    if href.startswith('http'):
                        job_data['link'] = href
                    elif href.startswith('/'):
                        job_data['link'] = f"https://worldbankgroup.csod.com{href}"
                    else:
                        job_data['link'] = f"https://worldbankgroup.csod.com/ux/ats/careersite/1/{href}"
                else:
                    link_elem = element.find('a', href=True)
                    if link_elem:
                        href = link_elem['href']
                        if href.startswith('http'):
                            job_data['link'] = href
                        elif href.startswith('/'):
                            job_data['link'] = f"https://worldbankgroup.csod.com{href}"
                        else:
                            job_data['link'] = f"https://worldbankgroup.csod.com/ux/ats/careersite/1/{href}"
                    else:
                        continue

                # Get job title
                if element.name == 'a':
                    job_data['title'] = element.get_text(strip=True)
                else:
                    title_elem = element.find(['h2', 'h3', 'h4', 'a'], class_=lambda x: x and 'title' in str(x).lower())
                    if not title_elem:
                        title_elem = element.find(['h2', 'h3', 'h4'])
                    if not title_elem:
                        title_elem = element.find('a')

                    if title_elem:
                        job_data['title'] = title_elem.get_text(strip=True)
                    else:
                        job_data['title'] = element.get_text(strip=True)[:100]

                # Skip if title is too short or generic
                if not job_data.get('title') or len(job_data['title']) < 5:
                    continue

                skip_keywords = ['search', 'filter', 'sort', 'login', 'sign in', 'home', 'about', 'contact']
                if any(keyword in job_data['title'].lower() for keyword in skip_keywords):
                    continue

                # Get location
                location_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'location' in str(x).lower())
                if not location_elem:
                    location_elem = element.find(string=lambda x: x and any(
                        loc in str(x) for loc in ['Washington', 'DC', 'Remote', 'Location:']
                    ))
                job_data['location'] = location_elem.get_text(strip=True) if location_elem else "World Bank Group"

                # Get department
                dept_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'department' in str(x).lower())
                job_data['department'] = dept_elem.get_text(strip=True) if dept_elem else ""

                # Create description
                description_parts = [job_data['title']]
                if job_data.get('location') and job_data['location'] != "World Bank Group":
                    description_parts.append(f"Location: {job_data['location']}")
                if job_data.get('department'):
                    description_parts.append(f"Department: {job_data['department']}")

                job_data['description'] = " | ".join(description_parts)

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

def generate_rss_feed(jobs, output_file='worldbank_jobs.xml'):
    """Generate RSS 2.0 feed from job listings"""

    # Register atom namespace
    ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')

    # Create RSS root element
    rss = ET.Element('rss', version='2.0')

    # Create channel element
    channel = ET.SubElement(rss, 'channel')

    # Add channel metadata
    title = ET.SubElement(channel, 'title')
    title.text = 'World Bank Group Jobs'

    link = ET.SubElement(channel, 'link')
    link.text = 'https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup'

    description = ET.SubElement(channel, 'description')
    description.text = 'Job listings from World Bank Group'

    language = ET.SubElement(channel, 'language')
    language.text = 'en-us'

    # Add atom:link for self-reference
    atom_link = ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link')
    atom_link.set('href', 'https://cinfoposte.github.io/worldbank-jobs/worldbank_jobs.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    # Add lastBuildDate
    last_build = ET.SubElement(channel, 'lastBuildDate')
    last_build.text = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Add job items
    for job in jobs:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        item_title.text = job.get('title', 'Untitled Position')

        item_link = ET.SubElement(item, 'link')
        item_link.text = job.get('link', '')

        item_description = ET.SubElement(item, 'description')
        item_description.text = job.get('description', '')

        # Add GUID
        guid = ET.SubElement(item, 'guid')
        guid.set('isPermaLink', 'true')
        guid.text = job.get('link', '')

    # Create pretty-printed XML
    xml_string = ET.tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print(f"\n[SUCCESS] RSS feed generated: {output_file}")
    print(f"  Total jobs in feed: {len(jobs)}")

def main():
    """Main execution function"""
    print("=" * 60)
    print("World Bank Group Job Scraper")
    print("=" * 60)

    # Scrape jobs
    jobs = scrape_worldbank_jobs()

    if jobs:
        # Generate RSS feed
        generate_rss_feed(jobs)
        print("\n[SUCCESS] Scraping completed successfully!")
    else:
        print("\n[ERROR] No jobs found. Please check the website structure.")

    print("=" * 60)

if __name__ == "__main__":
    main()
