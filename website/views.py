from django.shortcuts import render
from django.http import JsonResponse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import openai
from openai import OpenAI
from django.conf import settings
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import fitz  # PyMuPDF
import docx
import nltk
import logging


def IndexView(request):
    if request.method == 'POST':
        skills = request.POST.get('keyword', '')
        location = request.POST.get('location', '')
        experience = request.POST.get('experience', '')
        type_options = request.POST.getlist('type')
        types = ",".join(type_options)
        website_options = request.POST.getlist('website')

        data = job_data(skills, location, experience, types, website_options)

        return JsonResponse({"data": data}, status=200)

    return render(request, 'website/index.html')

def job_data(skills, location, experience, types, website_options):
    data = []

    def fetch_url(url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed to fetch data from {url}, Status code: {response.status_code}"}
        except Exception as e:
            return {"error": f"Exception occurred while fetching data from {url}: {str(e)}"}

    with ThreadPoolExecutor(max_workers=len(website_options)) as executor:
        futures = [
            executor.submit(
                fetch_url, 
                f"http://127.0.0.1:8000/{website}/scrape/?keywords={skills}&locations={location}&wfh_types={types}&experience={experience}"
            ) 
            for website in website_options
        ]

        for future in as_completed(futures):
            result = future.result()
            if 'jobs' in result:
                data.extend(result['jobs'])

    return data

@csrf_exempt
def chat_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '')

            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            function_descriptions = [
                {
                    "name": "get_job_info",
                    "description": "Find details for a job search from user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "The programming language or type of job, e.g. python, java, dev ops, backend, web development",
                            },
                            "location": {
                                "type": "string",
                                "description": "The location of the job site, e.g. india, kolkata, bangalore",
                            },
                            "experience": {
                                "type": "string",
                                "description": "The years of experience of the candidate, e.g. 1,2,3,4....",
                            },
                            "job_type": {
                                "type": "string",
                                "description": "The type of job he wants, e.g. remote, hybrid, office, work from home",
                            },
                            "websites": {
                                "type": "string",
                                "description": "The websites the job has to be found, e.g. naukri, indeed, linkedin, glassdoor",
                            },
                        },
                        "required": ["keyword"],
                    },
                },
                {
                    "name": "greetings",
                    "description": "Greets the user if they say something",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "greet": {
                                "type": "string",
                                "description": "Greets the user Eg. hi, hello, how are you",
                            }
                        },
                    },
                },
                {
                    "name": "help",
                    "description": "If they need any help",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "help": {
                                "type": "string",
                                "description": "If the user needs help. eg-help, tell, know",
                            }
                        },
                    },
                },
                {
                    "name": "owner",
                    "description": "Detail of the Owner(Shankhanil Ghosh)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Tell the user about the owner",
                            }
                        },
                    },
                },

            ]

            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_message}],
                functions=function_descriptions,
                function_call="auto",  # specify the function call
            )

            # Extract arguments from AI response
            function_call = completion.choices[0].message.function_call
            arguments = json.loads(function_call.arguments)

            print(arguments)

            if "greet" in arguments:
                return JsonResponse({'message': "Hi how are you doing. This is a scraping website created by Shankhanil Ghosh to solve and streamline the process of job hunt."})
            
            elif "help" in arguments:
                return JsonResponse({'message': "You can start searching with what type of job you want, python, java etc. and you can add location, your experience, the type of job you want and the websites you want the data from."})
            
            elif "owner" in arguments:
                return JsonResponse({
                    'message': "owner"
                })
            else:
                # Prepare response to send to frontend
                return_string = "Keyword(s): {} Location: {} Experience: {} years Job Type: {}".format(
                    arguments.get('keyword', 'Not specified'),
                    arguments.get('location', 'Not specified'),
                    arguments.get('experience', 'Not specified'),
                    arguments.get('job_type', 'Not specified')
                )

                return JsonResponse({'message': return_string, 'data': arguments})

        except json.JSONDecodeError as e:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

        except Exception as e:
            return JsonResponse({'error': 'Internal server error.'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


# Set up logging
log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'manual_debug.log')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(levelname)s %(asctime)s %(module)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

@csrf_exempt
def upload_resume(request):
    if request.method == 'POST' and request.FILES.get('resume'):
        resume = request.FILES['resume']
        logging.debug(f"Received resume file: {resume.name}")

        file_path = default_storage.save(resume.name, resume)
        file_full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        try:
            # Process the file here (e.g., extract text)
            if file_full_path.endswith('.pdf'):
                text = extract_text_from_pdf(file_full_path)
            elif file_full_path.endswith('.docx'):
                text = extract_text_from_docx(file_full_path)
            else:
                logging.error("Unsupported file format")
                return JsonResponse({'message': 'Unsupported file format'}, status=400)

            # Fetch resume details using OpenAI API
            resume_details = fetch_resume_details(text)
            logging.debug(f"Fetched resume details: {resume_details}")

            # Return the extracted information
            response_data = {
                'message': 'Resume processed successfully.',
                'data': resume_details
            }
            logging.debug(f"Processed resume details: {resume_details}")
        except Exception as e:
            logging.error(f"Error processing resume: {str(e)}", exc_info=True)
            return JsonResponse({'message': 'Error processing resume'}, status=500)
        finally:
            # Delete the file after processing
            if os.path.exists(file_full_path):
                os.remove(file_full_path)
                logging.debug(f"Deleted uploaded resume file: {file_full_path}")

        return JsonResponse(response_data)

    return JsonResponse({'message': 'No file uploaded'}, status=400)

# Helper functions to process resumes
def extract_text_from_pdf(pdf_path):
    text = ""
    document = fitz.open(pdf_path)
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text += page.get_text()
    logging.debug(f"Extracted text from PDF: {text[:200]}...")  # Log first 200 characters for brevity
    return text

def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = [paragraph.text for paragraph in doc.paragraphs]
    logging.debug(f"Extracted text from DOCX: {text[:200]}...")  # Log first 200 characters for brevity
    return '\n'.join(text)

def fetch_resume_details(text):
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    function_descriptions = [
        {
            "name": "get_resume_info",
            "description": "Find details from a resume",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Find the name of the candidate. Eg- ram, henry, abigail, Etc.",
                    },
                    "phone": {
                        "type": "string",
                        "description": "The 10 digit phone number of the candidate",
                    },
                    "location": {
                        "type": "string",
                        "description": "Location of the candidate Eg- delhi, kolkata, india, Etc.",
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address of the candidate Eg- xyz@abc.com",
                    },
                    "experience": {
                        "type": "string",
                        "description": "Add the total work experience of the candidate in years Eg- 1,2,2.3,4.5, Etc.",
                    },
                    "skills": {
                        "type": "string",
                        "description": "The type of skills the candidate has, e.g. java, python, web development, backend, data analyst, Etc.",
                    },
                },
                "required": ["name"],
            },
        }
    ]

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": text}],
        functions=function_descriptions,
        function_call="auto",
    )

    # Extract arguments from AI response
    function_call = completion.choices[0].message.function_call
    arguments = json.loads(function_call.arguments)

    logging.debug(f"Fetched resume details: {arguments}")

    return arguments