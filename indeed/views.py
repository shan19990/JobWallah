from django.http import JsonResponse
from urllib.parse import quote_plus
import requests
from .models import *
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import base64
from selenium.common.exceptions import TimeoutException
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def generate_indeed_url(keywords, locations=None, days_old=None, wfh_types=None, radius=100, start=0):
    base_url = "https://in.indeed.com/jobs"
    
    if not isinstance(keywords, list):
        raise ValueError("Keywords must be provided as a list")
    if not keywords:
        raise ValueError("Missing required parameter: keywords")

    # Join keywords with '+'
    joined_keywords = '+'.join(keywords).replace(' ', '+')

    # Handle locations parameter to use only the first location before comma ','
    if locations:
        if isinstance(locations, str):
            primary_location = locations.split(',')[0].strip()
        else:
            raise ValueError("Locations must be provided as a comma-separated string")
    else:
        primary_location = None

    query_params = {
        'q': joined_keywords,
        'l': primary_location,
        'from': 'searchOnDesktopSerp',
        'radius': str(radius),
        'start': str(start),
    }

    if wfh_types:
        # Check for mixed values and exclude sc parameter if mixed
        if ('0' in wfh_types or '1' in wfh_types) and ('2' in wfh_types or '3' in wfh_types):
            pass  # Do not include sc parameter if mixed
        else:
            sc_params = []
            for wfh_type in wfh_types:
                if wfh_type == '1' or wfh_type == '2':
                    sc_params.append('0kf%3Aattr%28DSQF7%29%3B')
                elif wfh_type == '0' or wfh_type == '3':
                    sc_params.append('0kf%3Aattr%28PAXZC%29%3B')

            if sc_params:
                query_params['sc'] = ','.join(sc_params)

    if days_old is not None:
        query_params['fromage'] = str(days_old)

    query_string = '&'.join([f"{key}={quote_plus(value)}" for key, value in query_params.items() if value is not None])
    full_url = f"{base_url}?{query_string}"
    
    return full_url.replace("%25", "%")


def scrape_indeed(request):
    try:
        keywords = request.GET.get('keywords')
        location = request.GET.get('locations')
        wfh_types = request.GET.get('wfh_types')
        start = int(request.GET.get('start', 0))  # Get start parameter, default to 0

        if not keywords:
            raise ValueError("Missing query parameter: keywords")

        keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        wfh_types_list = [wf.strip() for wf in wfh_types.split(',') if wf.strip()] if wfh_types else []

        url = generate_indeed_url(keywords_list, location, None, wfh_types_list, start=start)

        # Scrape job data
        jobs = scrape_indeed_from_url(url)

        return JsonResponse({"url":url,"jobs": jobs}, status=200)

    except ValueError as ve:
        return JsonResponse({"error": str(ve)}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def normalize_url(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    jk_param = query_params.get('jk', [''])[0]
    return f"https://{parsed_url.netloc}/viewjob?jk={jk_param}"


def scrape_indeed_from_url(url):
    try:
        options = Options()
        options.headless = True
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(2)

        # CAPTCHA detection
        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="captcha-element-id"]')))
            screenshot_data = driver.get_screenshot_as_png()
            screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
            driver.quit()
            return JsonResponse({"captcha_detected": True, "screenshot": screenshot_base64}, status=200)
        except TimeoutException:
            pass

        # Locate the job list container
        job_list_xpath = '//*[@id="mosaic-provider-jobcards"]//ul'
        ul_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, job_list_xpath)))
        li_elements = ul_element.find_elements(By.XPATH, './li')

        jobs = []
        for li in li_elements:
            job_dict = {}
            try:
                job_link_element = li.find_element(By.XPATH, './/h2/a')
                job_title = job_link_element.find_element(By.XPATH, './/span').text.strip()
                job_url = job_link_element.get_attribute('href')
                job_url = normalize_url(job_url)

                existing_job = Indeed.objects.filter(url=job_url).first()
                if existing_job:
                    job_dict.update({
                        'title': existing_job.title,
                        'url': existing_job.url,
                        'company': existing_job.company,
                        'location': existing_job.location,
                        'posted_date': existing_job.posted_date,
                        'salary': existing_job.salary,
                    })
                    jobs.append(job_dict)
                    continue

                company_name_element = li.find_element(By.XPATH, './/span[@data-testid="company-name"]')
                company_name = company_name_element.text.strip()

                location_element = li.find_element(By.XPATH, './/div[@data-testid="text-location"]')
                location = location_element.text.strip()

                posted_date_element = li.find_element(By.XPATH, './/span[@data-testid="myJobsStateDate"]')
                posted_date = posted_date_element.text.strip().replace('Posted', '').strip()

                driver.get(job_url)
                time.sleep(2)

                try:
                    salary_element = driver.find_element(By.ID, 'salaryInfoAndJobType')
                    salary = salary_element.text.strip().split('\n')[0]
                except:
                    salary = "Not disclosed"


                job_dict.update({
                    'title': job_title,
                    'url': job_url,
                    'company': company_name,
                    'location': location,
                    'posted_date': posted_date,
                    'salary': salary,
                })

                jobs.append(job_dict)

                Indeed.objects.create(
                    title=job_dict['title'],
                    url=job_dict['url'],
                    company=job_dict['company'],
                    location=job_dict['location'],
                    posted_date=job_dict['posted_date'],
                    salary=job_dict['salary'],
                )

                driver.back()
                time.sleep(2)
                
            except Exception as e:
                print(f"Error processing job: {str(e)}")
                continue
        
        driver.quit()
        return jobs

    except Exception as e:
        raise Exception(f"An error occurred: {str(e)}")
