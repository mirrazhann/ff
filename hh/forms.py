from django import forms
import os

# class ResumeForm(forms.ModelForm):
#     class Meta:
#         model = Resume
#         fields = ['file']
#         widgets = {
#             'Резюме (.pdf)': forms.FileInput(attrs={'class': 'form-control'}),
#         }

#         # Валидация файла .docs
#         def clean_file(self):
#             file = self.cleaned_data.get('file')
#             if file:
#                 ext = os.path.splitext(file.name)[1].lower()
#                 if ext != '.pdf':
#                     raise forms.ValidationError("Загружать можно только файлы формата .docx")
#             return file



class ErrorsInResumeForm(forms.Form):
    resume_id = forms.CharField(
        widget=forms.HiddenInput(),
    )

class DoBestResumeForm(forms.Form):
    resume_id = forms.CharField(
        widget=forms.HiddenInput(),
    )

class SearchVacancyInResumePage(forms.Form):
    resume_text = forms.CharField(
        widget=forms.HiddenInput(),
    )