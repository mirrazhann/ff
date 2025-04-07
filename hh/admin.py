from django.contrib import admin

# Register your models here.
from .models import Resume, HeadHunterToken

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'file_url', 'file', 'text')

@admin.register(HeadHunterToken)
class HeadHunterToken(admin.ModelAdmin):
    list_display = ('user', 'access_token', 'refresh_token', 'expires_at', 'updated_at')