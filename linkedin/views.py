from django.http import JsonResponse
from bs4 import BeautifulSoup
from .models import Linkedin
import requests
import time
from datetime import datetime, timedelta
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote_plus
from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs


def generate_linkedin_url(keywords, locations=None, experience=None, wfh_types=None, distance=100, origin="JOB_SEARCH_PAGE_JOB_FILTER", refresh=True):
    base_url = "https://www.linkedin.com/jobs/search/"
    
    if not isinstance(keywords, list):
        raise ValueError("Keywords must be provided as a list")
    if not keywords:
        raise ValueError("Missing required parameter: keywords")

    # Ensure keywords are in lowercase
    keywords = [keyword.lower() for keyword in keywords]
    
    # Experience mapping
    experience_mapping = {
        '0': '1',    # 0 years
        '2-3': '2',  # 2-3 years
        '4-5': '3',  # 4-5 years
        '6-8': '4',  # 6-8 years
        '9-15': '5', # 9-15 years
        '15+': '6'   # 15+ years
    }
    
    # Work-from-home types mapping
    wfh_mapping = {
        '0': '1',  # wfh_type = 0
        '1': '0',  # wfh_type = 1
        '2': '2',  # wfh_type = 2
        '3': '3'   # wfh_type = 3
    }

    # Convert numerical experience to a corresponding mapping key
    if experience:
        try:
            experience_int = int(experience)
            if experience_int == 0:
                f_E = experience_mapping['0']
            elif 2 <= experience_int <= 3:
                f_E = experience_mapping['2-3']
            elif 4 <= experience_int <= 5:
                f_E = experience_mapping['4-5']
            elif 6 <= experience_int <= 8:
                f_E = experience_mapping['6-8']
            elif 9 <= experience_int <= 15:
                f_E = experience_mapping['9-15']
            else:
                f_E = experience_mapping['15+']
        except ValueError:
            f_E = None
    else:
        f_E = None
    
    # Map work-from-home types
    if wfh_types:
        mapped_wfh_types = [wfh_mapping[str(wfh)] for wfh in wfh_types if str(wfh) in wfh_mapping]
        f_WT = '%2C'.join(mapped_wfh_types)
    else:
        f_WT = None

    # Set query parameters
    query_params = {
        'keywords': ','.join(keywords),
        'origin': origin,
        'refresh': 'true' if refresh else 'false',
        'distance': distance,
    }
    
    if f_E:
        query_params['f_E'] = f_E
    if f_WT:
        query_params['f_WT'] = f_WT

    if locations:
        primary_location = locations.split(',')[0].strip().lower()
        query_params['location'] = primary_location

    query_string = urlencode(query_params, safe='%2C')
    full_url = f"{base_url}?{query_string}"
    
    return full_url

def scrape_linkedin(request):
    try:
        keywords = request.GET.get('keywords')
        locations = request.GET.get('locations')
        wfh_types = request.GET.get('wfh_types')
        experience = request.GET.get('experience')

        if not keywords:
            raise ValueError("Missing query parameter: keywords")

        keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        wfh_types_list = [wf.strip() for wf in wfh_types.split(',') if wf.strip()] if wfh_types else []

        # Ensure experience is converted to an integer if provided
        experience_int = int(experience) if experience else None

        url = generate_linkedin_url(keywords_list, locations, experience_int, wfh_types_list)

        # Here you would implement the actual scraping of LinkedIn
        jobs = scrape_linkedin_from_url(url)

        return JsonResponse({"url": url, "jobs": jobs}, status=200)

    except ValueError as ve:
        return JsonResponse({"error": str(ve)}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def normalize_linkedin_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    position = query_params.get('position', [''])[0]
    jk_param = query_params.get('jk', [''])[0]
    base_url = f"https://{parsed_url.netloc}/jobs/view/{parsed_url.path.split('/')[-1].split('?')[0]}/{jk_param}"
    return base_url

def scrape_linkedin_from_url(url):
    driver = None
    try:
        options = Options()
        options.headless = True
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(2)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__results-list")))

        job_listings = driver.find_elements(By.CSS_SELECTOR, ".base-card")

        jobs = []
        main_window = driver.current_window_handle

        for job_elem in job_listings:
            try:
                job_dict = {}

                job_title = job_elem.find_element(By.CSS_SELECTOR, ".base-search-card__title").text.strip()
                company_name = job_elem.find_element(By.CSS_SELECTOR, ".base-search-card__subtitle a").text.strip()
                location = job_elem.find_element(By.CSS_SELECTOR, ".job-search-card__location").text.strip()
                posted_date = job_elem.find_element(By.CSS_SELECTOR, ".job-search-card__listdate").text.strip()
                job_url = job_elem.find_element(By.CSS_SELECTOR, ".base-card__full-link").get_attribute("href")

                job_url = normalize_linkedin_url(job_url)

                existing_job = Linkedin.objects.filter(url=job_url).first()
                if existing_job:
                    job_dict.update({
                        'title': existing_job.title,
                        'url': existing_job.url,
                        'company': existing_job.company,
                        'location': existing_job.location,
                        'posted_date': existing_job.posted_date,
                        'salary': existing_job.salary if existing_job.salary else "Not Disclosed",
                    })
                    jobs.append(job_dict)
                    continue

                Linkedin.objects.get_or_create(
                    title=job_title,
                    url=job_url,
                    company=company_name,
                    location=location,
                    posted_date=posted_date,
                )

                job_dict.update({
                    "title": job_title,
                    "url": job_url,
                    "company": company_name,
                    "location": location,
                    "posted_date": posted_date,
                })

                jobs.append(job_dict)
            except Exception as e:
                continue

        return jobs

    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")
    
    finally:
        if driver:
            driver.quit()