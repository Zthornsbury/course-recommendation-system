import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course, Student, CompletedCourse, Major
from courses.recommender import CourseRecommender
from datetime import date

# Get or create CSC major
csc_major = Major.objects.get(code='CSC')

# Create a test student
student, created = Student.objects.get_or_create(
    student_id='TEST001',
    defaults={
        'first_name': 'Test',
        'last_name': 'Student',
        'email': 'test@fsc.edu',
        'major': csc_major,
        'expected_graduation': date(2026, 5, 15)
    }
)
print(f"Student: {student.first_name} {student.last_name} (created={created})")

# Add some completed courses
completed_course_codes = ['CSC1980', 'CSC2280', 'CSC2290']

for course_code in completed_course_codes:
    course = Course.objects.get(course_code=course_code)
    completed, created = CompletedCourse.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            'semester': 'Fall 2025',
            'grade': 'A',
            'date_completed': date(2025, 12, 15)
        }
    )
    print(f"  Completed: {course_code} (created={created})")

# Test the recommender
print("\n" + "="*60)
print("TESTING RECOMMENDER ENGINE")
print("="*60)

recommender = CourseRecommender(student)

# Get recommendations
recommendations = recommender.get_recommendations(max_credits=18)

print(f"\nStudent: {student.student_id} - {student.first_name} {student.last_name}")
print(f"Major: {student.major.name}")
print(f"Completed courses: {len(recommender.completed_courses)}")

print(f"\n RECOMMENDED COURSES FOR NEXT SEMESTER:")
print(f"Total Credits: {recommendations['total_credits']}")
print(f"Remaining courses after this: {recommendations['remaining_to_complete']}\n")

for i, course in enumerate(recommendations['recommended'], 1):
    print(f"{i}. {course.course_code} - {course.course_name} ({course.credits} credits)")

print("\n" + "="*60)
