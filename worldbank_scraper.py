#!/usr/bin/env python3
"""
World Bank Group Job Scraper
Scrapes job listings from World Bank Group careers site and generates an RSS feed
Format: ADB-compatible for cinfoposte portal import
"""

import time
import os
import shutil
from datetime import datetime
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

def setup_driver():
    """Set up Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    # Find chromedriver in PATH (works with browser-actions/setup-chrome)
    chromedriver_path = shutil.which('chromedriver')
    if chromedriver_path:
        print(f"Using chromedriver at: {chromedriver_path}")
        service = Service(chromedriver_path)
    else:
        # Fallback to common location
        print("Using chromedriver from system path")
        service = Service('chromedriver')

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def generate_numeric_id(url):
    """Generate unique numeric ID from URL"""
    hash_object = hashlib.md5(url.encode())
    hex_dig = hash_object.hexdigest()
    # Take 12 characters to reduce collisions
    numeric_id = int(hex_dig[:12], 16) % 100000000  # 8 digits
    return str(numeric_id)

def get_existing_job_links(feed_file='worldbank_jobs.xml'):
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

def scrape_worldbank_jobs():
    """Scrape job listings from World Bank Group"""
    url = "https://worldbankgroup.csod.com/ux/ats/careersite/1/home?c=worldbankgroup"

    print(f"Starting scraper for: {url}")
    driver = setup_driver()
    jobs = []

    try:
        driver.get(url)
        print("Page loaded, waiting for JavaScript to render...")

        wait = WebDriverWait(driver, 30)
        print("Waiting for job content to load...")
        time.sleep(20)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        job_elements = []

        job_elements = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['job-card', 'job-item', 'position', 'vacancy', 'requisition']
        ))
        print(f"Strategy 1: Found {len(job_elements)} potential job elements")

        if not job_elements:
            job_links = soup.find_all('a', href=lambda x: x and 'requisition' in str(x).lower())
            job_elements = [link for link in job_links if len(link.get_text(strip=True)) > 5]
            print(f"Strategy 2: Found {len(job_elements)} job requisition links")

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

                if not job_data.get('title') or len(job_data['title']) < 5:
                    continue

                skip_keywords = ['search', 'filter', 'sort', 'login', 'sign in', 'home', 'about', 'contact']
                if any(keyword in job_data['title'].lower() for keyword in skip_keywords):
                    continue

                location_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'location' in str(x).lower())
                if not location_elem:
                    location_elem = element.find(string=lambda x: x and any(
                        loc in str(x) for loc in ['Washington', 'DC', 'Remote', 'Location:']
                    ))
                job_data['location'] = location_elem.get_text(strip=True) if location_elem else "Washington, DC"

                dept_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and 'department' in str(x).lower())
                job_data['department'] = dept_elem.get_text(strip=True) if dept_elem else ""

                description_parts = []
                description_parts.append(f"World Bank Group has a vacancy for the position of {job_data['title']}")
                if job_data.get('department'):
                    description_parts.append(f"in the {job_data['department']}")
                description_parts.append(f"Location: {job_data['location']}")

                # ElementTree will handle XML escaping automatically
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

def generate_rss_feed(jobs, output_file='worldbank_jobs.xml'):
    """Generate RSS 2.0 feed from job listings in ADB-compatible format"""

    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
    rss.set('xml:base', 'https://worldbankgroup.csod.com/')

    channel = ET.SubElement(rss, 'channel')

    title = ET.SubElement(channel, 'title')
    title.text = 'World Bank Group Job Vacancies'

    link = ET.SubElement(channel, 'link')
    link.text = 'https://worldbankgroup.csod.com/'

    description = ET.SubElement(channel, 'description')
    description.text = 'List of vacancies at the World Bank Group'

    language = ET.SubElement(channel, 'language')
    language.text = 'en'

    pub_date = ET.SubElement(channel, 'pubDate')
    current_time = datetime.utcnow()
    # RFC-822 format for channel pubDate
    pub_date.text = current_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

    for job in jobs:
        item = ET.SubElement(channel, 'item')

        item_title = ET.SubElement(item, 'title')
        # ElementTree handles XML escaping automatically
        item_title.text = job.get('title', 'Untitled Position')

        item_link = ET.SubElement(item, 'link')
        item_link.text = job.get('link', '')

        item_description = ET.SubElement(item, 'description')
        item_description.text = job.get('description', '')

        # Use numeric GUID per manual
        guid = ET.SubElement(item, 'guid')
        guid.set('isPermaLink', 'false')
        guid.text = generate_numeric_id(job.get('link', ''))

        # RFC-822 format for item pubDate
        item_pub_date = ET.SubElement(item, 'pubDate')
        item_pub_date.text = current_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

        source = ET.SubElement(item, 'source')
        source.set('url', 'https://worldbankgroup.csod.com/')
        source.text = 'World Bank Group Job Vacancies'

    xml_string = ET.tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_string)
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
    print("World Bank Group Job Scraper")
    print("=" * 60)

    existing_links = get_existing_job_links()
    all_jobs = scrape_worldbank_jobs()
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
        if not os.path.exists('worldbank_jobs.xml'):
            print("[INFO] Creating empty feed file")
            generate_rss_feed([])

    print("=" * 60)

if __name__ == "__main__":
    main()
