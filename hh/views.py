from django.shortcuts import render,  get_object_or_404
import requests
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse, JsonResponse

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login
from .forms import ErrorsInResumeForm, DoBestResumeForm, SearchVacancyInResumePage
from io import StringIO
from pdfminer.high_level import extract_text
from .models import Resume
import re
from django.utils import timezone
import datetime
from .models import HeadHunterToken
from openai import OpenAI
from django.contrib.auth.decorators import login_required



import asyncio


# Create your views here.
client = OpenAI(api_key=settings.OPEN_AI_KEY)

# авторизация на индексной странице, после авторизации проверяем авторизацию в hh
def index(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('hh:hh_auth') 
    else:
        form = AuthenticationForm(request)
    return render(request, 'hh/index.html', {'form': form})

# форма для загрузки резюме
# def resume_upload_form(request):
#     # if request.method == 'POST':
#     #     form = ResumeForm(request.POST, request.FILES)
#     #     if form.is_valid():
#     #         resume = form.save()
#     #         file_path = resume.file.path   
#     #         text = parse_resume(file_path) 
#     #         title = get_resume_title(text)  
#     #         resume.title = title
#     #         resume.text = text
#     #         resume.save()
#     #         return redirect('hh:resume_upload_success', resume_id=resume.id)
#     # else:
#     #     form = ResumeForm()
#     # return render(request, 'hh/resume_upload.html', {'form': form})
#     pass

# # страница подтверждения загрузки резюме
# def resume_upload_success(request, resume_id: int):
#     resume = get_object_or_404(Resume, id=resume_id)
#     return render(request, 'hh/resume_upload_success.html', {'resume': resume})

# # pdf парсинг
# def parse_resume(file_path: str):
#     return extract_text(file_path)

# Название резюме
# def get_resume_title(text: str):
#     pattern = r"Желаемая должность и зарплата[:\s]*(.*?)[\s]*Специализации:"
#     match = re.search(pattern, text, re.DOTALL)

#     if match:
#         result = match.group(1).strip()
#         # Удаляем все переносы строк и заменяем последовательности пробелов на один пробел
#         result_clean = re.sub(r'\s+', ' ', result)
#         return result_clean
#     else:
#         return ''
    
#     # doc = Document((file_path)
#     # full_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
#     # return full_text



# Авторизация в Хх
@login_required(login_url='/hh/')
def headhunter_login(request):
   
    auth_url = "https://hh.ru/oauth/authorize"  
    params = {
        'response_type': 'code',
        'client_id': settings.HEADHUNTER_CLIENT_ID,
        'redirect_uri': settings.HEADHUNTER_REDIRECT_URI,
    }
    url = f"{auth_url}?{urlencode(params)}"
    return redirect(url)

# код авторизации и токен
def headhunter_callback(request):
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Ошибка: код авторизации не получен", status=400)

    token_url = "https://hh.ru/oauth/token"
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.HEADHUNTER_REDIRECT_URI,
        'client_id': settings.HEADHUNTER_CLIENT_ID,
        'client_secret': settings.HEADHUNTER_CLIENT_SECRET,
    }

    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        result = f'Ошибка при обмене кода на токен: {response.text} <br> <a href="/hh/hh_auth">Получить код авторизации заново</a>'
        return HttpResponse(result, status=response.status_code)

    token_data = response.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in', 3600)  # число секунд до истечения токена

    expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)

    # Предполагаем, что пользователь уже аутентифицирован
    token_obj, created = HeadHunterToken.objects.get_or_create(user=request.user)
    token_obj.access_token = access_token
    token_obj.refresh_token = refresh_token
    token_obj.expires_at = expires_at
    token_obj.save()

    return redirect('hh:get_all_resumes')
    # return HttpResponse("Авторизация через HeadHunter прошла успешно!")

# Обновление токена
def refresh_hh_token(token_obj):
    # Если токен не истек, возвращаем текущий
    if not token_obj.is_expired():
        return token_obj.access_token

    token_url = "https://hh.ru/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': token_obj.refresh_token,
        'client_id': settings.HEADHUNTER_CLIENT_ID,
        'client_secret': settings.HEADHUNTER_CLIENT_SECRET,
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise Exception("Ошибка обновления токена")

    token_data = response.json()
    token_obj.access_token = token_data.get('access_token')
    token_obj.refresh_token = token_data.get('refresh_token')  # возможно, придёт новый refresh_token
    expires_in = token_data.get('expires_in', 3600)
    token_obj.expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)
    token_obj.save()

    return token_obj.access_token

# Запрос в хх
def get_hh_data(request, method: str, params: dict = None):
    # Предполагаем, что токен уже сохранён для текущего пользователя
    token_obj = HeadHunterToken.objects.get(user=request.user)
    access_token = refresh_hh_token(token_obj)
    
    headers = {'Authorization': f'Bearer {access_token}'}
    # params = {'host': 'hh.kz'}  # Передаем параметр host
    api_url = f"https://api.hh.ru/{method}"
    response = requests.get(api_url, headers=headers, params=params)
    
    # Обработка ответа API
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Ошибка запроса к API, нет результата", "status": response.status_code}


# Список резюме с hh
@login_required(login_url='/hh/')
def get_all_resumes(request):
    resumes = get_hh_data(request, 'resumes/mine')
    resumes_short_list = []
    for resume in resumes.get('items', []):
        resumes_short_list.append({
            'id': resume.get('id'),
            'title': resume.get('title'),
            'status': resume.get('status', {}).get('id'),
            'status_name': resume.get('status', {}).get('name'),
            'status_type': resume.get('access', {}).get('type', {}).get('id'),
            'status_type_name': resume.get('access', {}).get('type', {}).get('name')
        })
    
    # return JsonResponse(resumes_short_list, safe=False, json_dumps_params={'ensure_ascii': False}) 
    return render(request, 'hh/resume/resume.html', {'resumes': resumes_short_list})

# Список резюме с hh в json
@login_required(login_url='/hh/')
def get_all_resumes_json(request):
    resumes = get_hh_data(request, 'resumes/mine')
    resumes_short_list = []
    for resume in resumes.get('items', []):
        resumes_short_list.append({
            'id': resume.get('id'),
            'title': resume.get('title'),
            'status': resume.get('status', {}).get('id'),
            'status_name': resume.get('status', {}).get('name'),
            'status_type': resume.get('access', {}).get('type', {}).get('id'),
            'status_type_name': resume.get('access', {}).get('type', {}).get('name')
        })
    
    return JsonResponse(resumes_short_list, safe=False, json_dumps_params={'ensure_ascii': False}) 

# # резюме детально
@login_required(login_url='/hh/')
def get_resume(request, resume_id: str):
    resume = get_hh_data(request, f'/resumes/{resume_id}')
    # return JsonResponse(resume, safe=False, json_dumps_params={'ensure_ascii': False}) 
    if "error" not in resume:
        context = {
            'resume': resume,
        }
        return render(request, 'hh/resume/get_resume.html', context)
    else:
        # return JsonResponse(resume, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)

# ошибка
@login_required(login_url='/hh/')
def get_resume_error_page(request, error: str):
    return render(request, 'hh/resume/get_resume_error_page.html', {'error': error})

# # резюме детально json
@login_required(login_url='/hh/')
def get_resume_json(request, resume_id: str):
    resume = get_hh_data(request, f'/resumes/{resume_id}')
    return JsonResponse(resume, safe=False, json_dumps_params={'ensure_ascii': False}) 

# Подготовка резюме для openai
def prepare_resume_for_openai(request, resume_data, form_type: str = None):
    
    if not resume_data:
        return "Нет данных резюме"

    total_text = ''

    # Название резюме
    title = resume_data.get("title", "")
    total_text += title + "\n"

    # Пример обработки: собираем текст из поля "skills"
    skills = resume_data.get("skills", "")
    total_text += "Цель: " + skills + "\n"

    # Обработка опыта работы (предполагаем, что это список словарей)
    experience_text = "Стаж работы: \n"
    for exp in resume_data.get("experience", []):
        experience_text += f"Компания: {exp.get('company', '')}\n"
        experience_text += f"Должность: {exp.get('position', '')}\n"
        experience_text += f"Описание: {exp.get('description', '')}\n"
    total_text += experience_text

    # Обработка образования (пример для основного образования)
    education_text = "Образование: \n"
    for edu in resume_data.get("education", {}).get("primary", []):
        education_text += f"{edu.get('name', '')}\n"
        education_text += f"{edu.get('result', '')}\n"
    total_text += education_text

    # Обработка дополнительного образования
    additional_text = "Доп. образование: \n"
    for additional in resume_data.get("education", {}).get("additional", []):
        additional_text += f"{additional.get('organization', '')}\n"
        additional_text += f"{additional.get('name', '')}\n"
    total_text += additional_text

    # Обработка сертификатов
    certificate_text = "Сертификаты: \n"
    for cert in resume_data.get("education", {}).get("attestation", []):
        certificate_text += f"{cert.get('organization', '')}\n"
        certificate_text += f"{cert.get('name', '')}\n"
    total_text += certificate_text

    # Дополнительная обработка, если form_type задан как 'best_resume'
    if form_type == 'best_resume':
        skills_list_text = "Навыки: \n"
        for skill in resume_data.get("skill_set", []):
            skills_list_text += f"{skill}; "
        total_text += skills_list_text

    return total_text

def send_to_openai(text: str):
    prompt = (text)
    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "input_text",
                    "text": prompt
                    }
                ]
                }
            ],
            text={
                "format": {
                "type": "text"
                }
            },
            reasoning={},
            tools=[],
            temperature=1,
            max_output_tokens=2048,
            top_p=1,
            store=True
        )
        # Новый API возвращает результат в виде атрибута output
        return response.output
    except Exception as e:
        return f"Ошибка при запросе к OpenAI: {e}"
    
@login_required(login_url='/hh/')    
def get_resume_find_errors(request, resume_id: str):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    if "error" in resume_data:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume_data["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)

    text = prepare_resume_for_openai(request, resume_data)
    prompt = f"Ты ассистент, который проверяет резюме на наличие грамматических и пунктуационных ошибок.\nПроанализируй следующее резюме:\n{text}"
    ai_text = send_to_openai(prompt)
    resume = get_hh_data(request, f'/resumes/{resume_id}')
    context = {
        'resume': resume,
        'ai_text': ai_text
    }

    return render(request, 'hh/resume/get_resume_with_ai_errors.html', context)
 
@login_required(login_url='/hh/')    
def get_resume_best(request, resume_id: str):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    if "error" in resume_data:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume_data["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)

    text = prepare_resume_for_openai(request, resume_data, 'best_resume')
    prompt = f"Ты ассистент, который улучшает содержимое резюме. Какие описания необходимо доработать и как, чтобы оно стало более продающим. Каких пунктов и деталей не хватает в резюме?:\n{text}"
    
    ai_text = send_to_openai(prompt)
    resume = get_hh_data(request, f'/resumes/{resume_id}')
    context = {
        'resume': resume,
        'ai_text': ai_text
    }

    return render(request, 'hh/resume/get_resume_with_ai_best.html', context)

@login_required(login_url='/hh/')
def get_resume_vacancy(request, resume_id: str):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    if "error" in resume_data:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume_data["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)
    text = ''
    title = resume_data.get("title", "")
    text += title + "; "
    # for skill in resume_data.get("skill_set", []):
    #     text += f"{skill}; "

    params = {
        'host': 'hh.kz',
        'area': 160,
        'text': text,
        'per_page': 100
    }
    vacancy_list = get_hh_data(request, 'vacancies', params)
    vacancy_short_list = []
    for vacancy in vacancy_list.get('items', []):

        salary_range_data = vacancy.get('salary_range') or {}

        salary_range_from = salary_range_data.get('from')
        if salary_range_from is None:
            salary_range_from = ""

        salary_range_to = salary_range_data.get('to')
        if salary_range_to is None:
            salary_range_to = ""

        salary_range_currency = salary_range_data.get('currency')
        if salary_range_currency is None:
            salary_range_currency = ""

        salary_range_gross = salary_range_data.get('gross')
        if salary_range_gross is None:
            salary_range_gross = ""

        mode_data = salary_range_data.get('mode') or {}
        salary_range_mode_name = mode_data.get('name') or ""


        #     return JsonResponse(vacancy.get('salary_range', {}).get('from'), safe=False, json_dumps_params={'ensure_ascii': False})  
        # salary_from = "" if vacancy.get('salary_range', {}).get('from') == None else vacancy.get('salary_range', {}).get('from')

        vacancy_short_list.append({
            'id': vacancy.get('id'),
            'name': vacancy.get('name'),
            'city': vacancy.get('area', {}).get('name'),
            'employer_name': vacancy.get('employer', {}).get('name'),
            'salary_from': salary_range_from,
            'salary_to': salary_range_to,
            'salary_currency': salary_range_currency,
            'salary_gross': salary_range_gross,
            'salary_mode': salary_range_mode_name,
            'experience': vacancy.get('experience', {}).get('name'),
        })

    context = {
        'resume': resume_data,
        'vacancy_list': vacancy_short_list
    }

    return render(request, 'hh/resume/get_resume_with_vacancy_list.html', context)
    
@login_required(login_url='/hh/')
def get_resume_vacancy_json(request, resume_id: str):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    if "error" in resume_data:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume_data["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)
    text = ''
    title = resume_data.get("title", "")
    text += title + "; "
    # for skill in resume_data.get("skill_set", []):
    #     text += f"{skill}; "

    params = {
        'host': 'hh.kz',
        'area': 160,
        'text': text,
        'per_page': 100
    }
    vacancy_list = get_hh_data(request, 'vacancies', params)
    vacancy_short_list = []
    for vacancy in vacancy_list.get('items', []):

        salary_range_data = vacancy.get('salary_range') or {}

        salary_range_from = salary_range_data.get('from')
        if salary_range_from is None:
            salary_range_from = ""

        salary_range_to = salary_range_data.get('to')
        if salary_range_to is None:
            salary_range_to = ""

        salary_range_currency = salary_range_data.get('currency')
        if salary_range_currency is None:
            salary_range_currency = ""

        salary_range_gross = salary_range_data.get('gross')
        if salary_range_gross is None:
            salary_range_gross = ""


        mode_data = salary_range_data.get('mode') or {}
        salary_range_mode_name = mode_data.get('name') or ""


        #     return JsonResponse(vacancy.get('salary_range', {}).get('from'), safe=False, json_dumps_params={'ensure_ascii': False})  
        # salary_from = "" if vacancy.get('salary_range', {}).get('from') == None else vacancy.get('salary_range', {}).get('from')

        vacancy_short_list.append({
            'id': vacancy.get('id'),
            'name': vacancy.get('name'),
            'city': vacancy.get('area', {}).get('name'),
            'employer_name': vacancy.get('employer', {}).get('name'),
            'salary_from': salary_range_from,
            'salary_to': salary_range_to,
            'salary_currency': salary_range_currency,
            'salary_gross': salary_range_gross,
            'salary_mode': salary_range_mode_name,
            'experience': vacancy.get('experience', {}).get('name'),
        })

    return JsonResponse(vacancy_short_list, safe=False, json_dumps_params={'ensure_ascii': False}) 

@login_required(login_url='/hh/')
def get_resume_vacancy_detail(request, resume_id: str, vacancy_id: int):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    vacancy = get_hh_data(request, f'vacancies/{vacancy_id}')

    published_at_str = vacancy.get('published_at')
    if published_at_str:
        published_date = published_at_str.split("T")[0]
    else:
        published_date = ""

    vacancy['published_date'] = published_date

    context = {
        'resume': resume_data,
        'vacancy': vacancy
    }
    return render(request, 'hh/resume/get_resume_with_vacancy_detail.html', context)

@login_required(login_url='/hh/')
def get_resume_vacancy_detail_json(request, resume_id: str, vacancy_id: int):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    vacancy = get_hh_data(request, f'vacancies/{vacancy_id}')

    published_at_str = vacancy.get('published_at')
    if published_at_str:
        published_date = published_at_str.split("T")[0]
    else:
        published_date = ""

    vacancy['published_date'] = published_date
    
    return JsonResponse(vacancy, safe=False, json_dumps_params={'ensure_ascii': False}) 

@login_required(login_url='/hh/')
def get_resume_vacancy_check(request, resume_id: str, vacancy_id: int):
    resume_data = get_hh_data(request, f'/resumes/{resume_id}')
    if "error" in resume_data:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': resume_data["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)

    resume_text = prepare_resume_for_openai(request, resume_data, 'best_resume')

    vacancy = get_hh_data(request, f'vacancies/{vacancy_id}')
    if "error" in vacancy:
        # return JsonResponse(resume_data, safe=False, json_dumps_params={'ensure_ascii': False}) 
        context = {
            'error': vacancy["error"],
        }
        return render(request, 'hh/resume/get_resume_error_page.html', context)
    
    vacancy_text = prepare_vacancy_for_openai(request, resume_data)


    prompt = f"Ты HR-специались, который анализирует, насколько данные из резюме подходят под требования к вакансии. Так же ты можешь предложить ресурсы, для прокачки определенных навыков, которых не хватает в резюме. \n Резюме - {resume_text}\n Вакансия - {vacancy_text}"
    
    ai_text = send_to_openai(prompt)
    context = {
        'resume': resume_data,
        'vacancy': vacancy,
        'ai_text_resume_and_vacancy': ai_text
    }

    return render(request, 'hh/resume/get_resume_with_vacancy_detail_check.html', context)


# Подготовка вакансии для openai
def prepare_vacancy_for_openai(request, vacancy_data, form_type: str = None):
    
    if not vacancy_data:
        return "Нет данных резюме"

    total_text = ''

    description = vacancy_data.get("description", "")
    total_text += "Описание: " + description + "\n"

    # Дополнительная обработка, если form_type задан как 'best_resume'

    skills_list_text = "Навыки: \n"
    for skill in vacancy_data.get("key_skills", []):
        skills_list_text += f"{skill}; "
    total_text += skills_list_text

    return total_text