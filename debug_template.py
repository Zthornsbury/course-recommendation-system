import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from django.template.loader import render_to_string
from courses.models import Student, Major

# Get the student
student = Student.objects.get(student_id='TEST001')

# Try to render the template
try:
    html = render_to_string('courses/dashboard.html', {'student': student})
    print("Template rendered successfully!")
    print(f"Student name in template: {student.first_name} {student.last_name}")
except Exception as e:
    print(f"Error rendering template: {e}")
    import traceback
    traceback.print_exc()