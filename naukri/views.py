from django.http import JsonResponse
from bs4 import BeautifulSoup
from .models import Naukri
import requests
import time
from datetime import datetime, timedelta
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote_plus


def generate_naukri_url(keywords, locations=None, experience=None, start=0, wfh_types=None):
    base_url = "https://www.naukri.com"
    
    if not isinstance(keywords, list):
        raise ValueError("Keywords must be provided as a list")
    if not keywords:
        raise ValueError("Missing required parameter: keywords")
    if locations and not isinstance(locations, list):
        raise ValueError("Locations must be provided as a list")

    keywords = [keyword.lower() for keyword in keywords]
    locations = [location.lower() for location in locations] if locations else None

    # Combine keywords for the path
    combined_keywords = '-'.join(keywords)
    
    if locations:
        if start > 0:
            path = f"/{combined_keywords}-jobs-in-{locations[0]}-{start}"
        else:
            path = f"/{combined_keywords}-jobs-in-{locations[0]}"
    else:
        if start > 0:
            path = f"/{combined_keywords}-jobs-{start}"
        else:
            path = f"/{combined_keywords}-jobs"

    query_params = {
        'k': ', '.join(keywords),
        'l': ', '.join(locations) if locations else None,
        'experience': str(experience) if experience is not None else None,
        'nignbevent_src': 'jobsearchDeskGNB'
    }

    # Initialize query string
    query_string = '&'.join([f"{key}={quote_plus(value)}" for key, value in query_params.items() if value is not None])

    # Add wfhTypes as separate parameters
    if wfh_types:
        for wfh_type in wfh_types:
            query_string += f"&wfhType={quote_plus(wfh_type)}"

    full_url = f"{base_url}{path}?{query_string}"
    
    return full_url


def scrape_naukri(request):
    try:
        keywords = request.GET.get('keywords')
        locations = request.GET.get('locations')
        experience = request.GET.get('experience', 0)
        start = int(request.GET.get('start', 0))  # Get start parameter, default to 0
        wfh_types = request.GET.get('wfh_types')  # Get wfh_types as a comma-separated string

        if not keywords:
            raise ValueError("Missing query parameter: keywords")

        keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        locations_list = [loc.strip() for loc in locations.split(',') if loc.strip()] if locations else []
        wfh_types_list = [wfh.strip() for wfh in wfh_types.split(',') if wfh.strip()] if wfh_types else []

        url = generate_naukri_url(keywords_list, locations_list, experience, start, wfh_types_list)
        
        # Check if jobs already exist in the database
        return scrape_naukri_from_url(url)

    except ValueError as ve:
        return JsonResponse({"error": str(ve)}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def scrape_naukri_from_url(url):
    try:
        options = Options()
        options.headless = True

        driver = webdriver.Chrome(options=options)

        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_elements = soup.find_all('div', class_='srp-jobtuple-wrapper')

        jobs = []
        for job_elem in job_elements:
            job_dict = {}
            row1 = job_elem.find('div', class_='row1')
            if row1:
                title_elem = row1.find('a', class_='title')
                if title_elem:
                    title = title_elem.text.strip()
                    joburl = title_elem.get('href')

                    # Check if job details are already in the database
                    existing_job = Naukri.objects.filter(url=joburl).first()
                    if existing_job:
                        job_dict.update({
                            'title': existing_job.title,
                            'url': existing_job.url,
                            'company': existing_job.company,
                            'experience': existing_job.experience,
                            'salary': existing_job.salary,
                            'location': existing_job.location,
                            'posted_date': existing_job.posted_date,
                        })
                        jobs.append(job_dict)
                        continue
                    else:
                        job_dict.update({
                            'title': title,
                            'url': joburl
                        })
                    
            
            row2 = job_elem.find('div', class_='row2')
            if row2:
                company = row2.text.strip()
                job_dict.update({
                    'company': company
                })

            row3 = job_elem.find('div', class_='row3')
            if row3:
                spans = row3.find_all('span')
                if len(spans) >= 3:
                    experience = spans[0].text.strip()
                    salary = spans[4].text.strip()
                    location = spans[7].text.strip()

                    job_dict.update({
                        'experience': experience,
                        'salary': salary,
                        'location': location
                    })

            row6 = job_elem.find('div', class_='row6')
            if row6:
                relative_time = row6.text.strip('save')
                job_dict.update({
                    'posted_date': relative_time
                })

            # Save the new job to the database
            Naukri.objects.create(**job_dict)
            jobs.append(job_dict)

        driver.quit()
        return JsonResponse({"url": url, "jobs": jobs}, status=200)

    except Exception as e:
        driver.quit()
        return JsonResponse({"error": str(e)}, status=500)
