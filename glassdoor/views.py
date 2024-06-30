from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.http import JsonResponse
from .models import Glassdoor  # Import your Glassdoor model
import time

def scrape_glassdoor(request):
    try:
        keywords = request.GET.get('keywords')
        location = request.GET.get('location')
        wfh_types = request.GET.get('wfh_types')

        if not keywords:
            raise ValueError("Missing query parameter: keywords")

        keywords_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        
        jobs = search_jobs(keywords_list[0], location, wfh_types)  # Using the first keyword

        return JsonResponse({"jobs": jobs}, status=200)

    except ValueError as ve:
        return JsonResponse({"error": str(ve)}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def search_jobs(keyword, location, wfh_types):
    # Handle None values for keyword and location
    if not keyword:
        keyword = ''
    if not location:
        location = ''

    # Check if jobs for the given keyword and location already exist in the database
    existing_jobs = Glassdoor.objects.filter(title__icontains=keyword, location__icontains=location)
    if existing_jobs.exists():
        # If jobs are found in the database, return them
        return list(existing_jobs.values('title', 'url', 'company', 'experience', 'salary', 'location', 'posted_date'))

    options = Options()
    options.headless = False
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://www.glassdoor.co.in/Job/index.htm")

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "searchBar-location"))
        )

        # Find the keyword input field and enter the keyword
        keyword_input = driver.find_element(By.ID, "searchBar-jobTitle")
        keyword_input.clear()
        keyword_input.send_keys(keyword)
        
        # Find the location input field and enter the location
        location_input = driver.find_element(By.ID, "searchBar-location")
        location_input.clear()
        location_input.send_keys(location)
        location_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Check if the wfh_types contain '1' or '2' and append the parameter to the URL
        if wfh_types and any(type in ['1', '2'] for type in wfh_types.split(',')):
            driver.get(driver.current_url + "?remoteWorkType=1")
            # Wait for the new results page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="left-column"]/div[2]/ul'))
            )

        # Wait for the results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="left-column"]/div[2]/ul'))
        )

        # Collect job results
        ul_element = driver.find_element(By.XPATH, '//*[@id="left-column"]/div[2]/ul')
        li_elements = ul_element.find_elements(By.TAG_NAME, 'li')
        
        jobs = []
        for li in li_elements:
            try:
                job_title_element = li.find_element(By.CLASS_NAME, 'JobCard_jobTitle___7I6y')
                job_title = job_title_element.text
                job_url = job_title_element.get_attribute('href')

                company_name = li.find_element(By.CLASS_NAME, 'EmployerProfile_compactEmployerName__LE242').text
                city = li.find_element(By.CLASS_NAME, 'JobCard_location__rCz3x').text
                salary = li.find_element(By.CLASS_NAME, 'JobCard_salaryEstimate__arV5J').text.strip(" (Glassdoor Est.)").strip('(Employe') if li.find_elements(By.CLASS_NAME, 'JobCard_salaryEstimate__arV5J') else 'Not Disclosed'
                posted_date = li.find_element(By.CLASS_NAME, 'JobCard_listingAge__Ny_nG').text
                experience = "N/A"  # Set to 'N/A' as placeholder since it's not scraped here
                
                job = {
                    'title': job_title,
                    'url': job_url,
                    'company': company_name,
                    'experience': experience,
                    'salary': salary,
                    'location': city,
                    'posted_date': posted_date
                }
                
                jobs.append(job)

                # Save job to database
                Glassdoor.objects.create(
                    title=job_title,
                    url=job_url,
                    company=company_name,
                    experience=experience,
                    salary=salary,
                    location=city,
                    posted_date=posted_date
                )

            except Exception as e:
                print(f"Error parsing job element: {e}")
    
        return jobs

    finally:
        driver.quit()
