from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'hh'
urlpatterns = [
    path('hh_auth/', views.headhunter_login, name='hh_auth'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('callback/', views.headhunter_callback, name='headhunter_callback'),
    # path('resume_upload/', views.resume_upload_form, name='resume_upload_form'),
    # path('resume_upload_success/<int:resume_id>/', views.resume_upload_success, name='resume_upload_success'),
    path('', views.index, name='index'),
    path('resume/', views.get_all_resumes, name='get_all_resumes'),
    path('resume/json/', views.get_all_resumes_json, name='get_all_resumes_json'),
    path('resume/<str:resume_id>/', views.get_resume, name='get_resume'),
    path('resume/<str:resume_id>/json/', views.get_resume_json, name='get_resume_json'),
    path('resume/<str:resume_id>/find_errors/', views.get_resume_find_errors, name='get_resume_find_errors'),
    path('resume/<str:resume_id>/best/', views.get_resume_best, name='get_resume_best'),
    path('resume/<str:resume_id>/vacancy/<int:vacancy_id>/check/', views.get_resume_vacancy_check, name='get_resume_vacancy_check'),
    path('resume/<str:resume_id>/vacancy/', views.get_resume_vacancy, name='get_resume_vacancy'),
    path('resume/<str:resume_id>/vacancy/json/', views.get_resume_vacancy_json, name='get_resume_vacancy_json'),
    path('resume/<str:resume_id>/vacancy/<int:vacancy_id>/', views.get_resume_vacancy_detail, name='get_resume_vacancy_detail'),
    path('resume/<str:resume_id>/vacancy/<int:vacancy_id>/json/', views.get_resume_vacancy_detail_json, name='get_resume_vacancy_detail_json'),
    path('resume/error', views.get_resume_error_page, name='get_resume_error_page'),
]
# hh/resume/get_resume_error_page.html
# /hh/search? - поиск вакансий
# /hh/vacancy/ - список сохраненных вакансий 
# /hh/vacancy/id - вакансия детально
# /hh/vacancy/id/resume_id/ - анализ вакансии и резюме с помощью чата jpt
# /hh/resumes/ - список моих резюме
# /hh/resume/id - резюме детально
# /hh/bot/send - отправка резюме телеграмм ботом