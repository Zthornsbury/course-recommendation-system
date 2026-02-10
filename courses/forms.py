from django import forms
from courses.models import CompletedCourse, Course

class AddCompletedCourseForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=CompletedCourse.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}), label='Selected Course')
    grade = forms.ChoiceField(choices=CompletedCourse.GRADE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}), label='Grade')

    class Meta:
        model = CompletedCourse
        fields = ('course', 'grade')
        widgets = {
            'semester': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Fall 2025'}),
        }