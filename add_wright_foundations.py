import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course, DegreeRequirement, Major

# WRIGHT Foundation Requirements from FSC Catalog
wright_courses = [
    # A. Written Communication (4 hours - choose from options)
    {'code': 'ENG1005', 'name': 'Writing About Topics', 'credits': 4, 'dept': 'English', 'semester': 'Both'},

    # B. Oral Communication (4 hours - choose from options)
    {'code': 'COM1500', 'name': 'Speak for Success', 'credits': 4, 'dept': 'Communication', 'semester': 'Both'},

    # R: Resilience (2 hours)
    {'code': 'DPT2000', 'name': 'Strategic Resilience: Building Strength for Life', 'credits': 2,
     'dept': 'General Education', 'semester': 'Both'},

    # I: Investigating Connections in Social/Behavioral Sciences (4 hours)
    {'code': 'PSY1106', 'name': 'Psychology and the Social World', 'credits': 4, 'dept': 'Psychology',
     'semester': 'Both'},
    {'code': 'SOC1100', 'name': 'Introduction to Sociology', 'credits': 4, 'dept': 'Sociology', 'semester': 'Both'},

    # G: Global Perspectives (4 hours)
    {'code': 'HIS1300', 'name': 'The Modern World', 'credits': 4, 'dept': 'History', 'semester': 'Both'},

    # H: Humanities & Fine Arts (8 hours - 4 Humanities + 4 Fine Arts)
    # Humanities (4 hours)
    {'code': 'PHI2304', 'name': 'Ethics', 'credits': 4, 'dept': 'Philosophy', 'semester': 'Both'},
    {'code': 'REL2314', 'name': 'Christian Ethics', 'credits': 4, 'dept': 'Religion', 'semester': 'Both'},

    # Fine Arts (4 hours)
    {'code': 'ART1100', 'name': 'History of Art and Architecture', 'credits': 4, 'dept': 'Art', 'semester': 'Both'},
    {'code': 'MUS1101', 'name': 'Chamber Singers', 'credits': 4, 'dept': 'Music', 'semester': 'Both'},

    # T: Technology, Math and Natural Science (8 hours - 4 Natural Science + 4 Math)
    # Natural Science (4 hours)
    {'code': 'BIO1005', 'name': 'Topics in Biology', 'credits': 4, 'dept': 'Biology', 'semester': 'Both'},
    {'code': 'BIO1050', 'name': 'Biology I: Biological Essentials', 'credits': 4, 'dept': 'Biology',
     'semester': 'Both'},
    {'code': 'CHE1050', 'name': 'Principles of Chemistry I', 'credits': 4, 'dept': 'Chemistry', 'semester': 'Both'},

    # Mathematics (4 hours - already have CSC2100/MAT2100 Discrete Mathematics)
    # Adding a few more math options
    {'code': 'MAT2022', 'name': 'Elementary Statistics', 'credits': 4, 'dept': 'Mathematics', 'semester': 'Both'},
    {'code': 'MAT2100', 'name': 'Discrete Mathematics', 'credits': 4, 'dept': 'Mathematics', 'semester': 'Both'},
]


def import_wright_courses():
    print("=" * 60)
    print("IMPORTING WRIGHT FOUNDATION COURSES")
    print("=" * 60 + "\n")

    for course_data in wright_courses:
        course, created = Course.objects.update_or_create(
            course_code=course_data['code'],
            defaults={
                'course_name': course_data['name'],
                'credits': course_data['credits'],
                'description': f"WRIGHT Foundation requirement in {course_data['dept']}.",
                'department': course_data['dept'],
                'semester_offered': course_data['semester']
            }
        )

        if created:
            print(f"✓ Created: {course.course_code} - {course.course_name}")
        else:
            print(f"✓ Updated: {course.course_code} - {course.course_name}")

    print("\n" + "=" * 60)
    print("ADDING TO CSC MAJOR REQUIREMENTS")
    print("=" * 60 + "\n")

    # Add to CSC major requirements
    try:
        csc_major = Major.objects.get(code='CSC')

        for course_data in wright_courses:
            course = Course.objects.get(course_code=course_data['code'])
            deg_req, created = DegreeRequirement.objects.get_or_create(
                major=csc_major,
                course=course,
                defaults={
                    'requirement_type': 'REQUIRED',
                    'credits_required': course.credits
                }
            )

            if created:
                print(f"✓ Added {course.course_code} to CSC requirements")

        print("\n" + "=" * 60)
        print("✅ WRIGHT FOUNDATION COURSES IMPORTED SUCCESSFULLY!")
        print("=" * 60)

    except Major.DoesNotExist:
        print("\n⚠️  ERROR: CSC Major not found in database!")
        print("Please create the CSC major first in the admin panel.")


if __name__ == '__main__':
    import_wright_courses()
