import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course

# Courses offered BOTH semesters (appear in both Fall and Spring)
both_semesters = [
    'CSC2100', 'CSC2280', 'CSC2290', 'CSC3280', 'CSC3310',
    'CSC3340', 'CSC3380', 'CSC3400'
]

# Courses offered FALL only
fall_only = [
    'CSC1980',  # Freshman Seminar
    'CSC3520',  # Machine Learning
    'CSC3810',  # Computer Networking
    'CSC4610',  # Advanced Web Dev
    'CSC4810',  # Threat Detection
    'CSC4899',  # Senior Project
]

# Courses offered SPRING only
spring_only = [
    'CSC3820',  # Penetration Testing
    'CSC4410',  # Operating Systems
    'CSC4510',  # Advanced AI
    'CSC4640',  # Programming Languages
]

print("Updating CSC courses based on FSC Portal data...")
print("="*70)

# Update Both
for code in both_semesters:
    try:
        course = Course.objects.get(course_code=code)
        course.semester_offered = 'Both'
        course.save()
        print(f"✓ {code} → Both")
    except Course.DoesNotExist:
        print(f"✗ {code} not found")

# Update Fall only
for code in fall_only:
    try:
        course = Course.objects.get(course_code=code)
        course.semester_offered = 'Fall'
        course.save()
        print(f"✓ {code} → Fall")
    except Course.DoesNotExist:
        print(f"✗ {code} not found")

# Update Spring only
for code in spring_only:
    try:
        course = Course.objects.get(course_code=code)
        course.semester_offered = 'Spring'
        course.save()
        print(f"✓ {code} → Spring")
    except Course.DoesNotExist:
        print(f"✗ {code} not found")

print("\n" + "="*70)
print("✅ All CSC course semesters updated based on FSC Portal!")
print("\nNote: Other courses not in portal remain 'Both' (electives/special topics)")
