from django.db import models
from django.utils import timezone
from django.conf import settings

# Create your models here.

# hh_auth_token
# token, refresh_token
class HeadHunterToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)  # время, когда access_token станет недействителен
    updated_at = models.DateTimeField(null=True, auto_now=True)

    def is_expired(self):
        return self.expires_at and self.expires_at <= timezone.now()

# hh_my_resumes
# resume_id, active/status
class Resume(models.Model):
    status = models.TextField()
    text = models.TextField()
    file_url = models.TextField()
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='resumes/', null=True, blank=True)
    hh_resume_id = models.IntegerField(null=True)

    def __str__(self):
        return f"Resume {self.id}"

# hh_vacancy
# vacancy_id, is_favorite, был_отклик

class Vacancy(models.Model):
    vacancy_id = models.IntegerField(unique=True, db_index=True)
    status = models.TextField()

# сопроводительные тексты
class CoverLetter(models.Model):
    resume_id = models.ForeignKey(Resume, on_delete=models.CASCADE)
    text = models.TextField()
    
# vacancy_search
