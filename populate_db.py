import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course, Major, Prerequisite, DegreeRequirement

# Create the CSC Major
csc_major, created = Major.objects.get_or_create(
    code='CSC',
    defaults={
        'name': 'Computer Science',
        'description': 'Bachelor of Science in Computer Science',
        'total_credits_required': 124
    }
)
print(f"CSC Major: {csc_major.name} (created={created})")

# Core CSC Courses
core_courses = [
    ('CSC1980', 'Exploring Computer Science', 1, 'Foundational course introducing computer science concepts'),
    ('CSC2280', 'Introduction to Computer Science', 4, 'Introduction to computer science principles and programming'),
    ('CSC2290', 'Object-Oriented Programming', 4, 'Programming using object-oriented principles'),
    ('CSC3280', 'Data Structures', 4, 'Study of data structures including lists, stacks, queues, trees'),
    ('CSC3310', 'Computer Organization and Architecture', 4, 'Computer hardware organization and architecture'),
    ('CSC3380', 'Algorithms', 4, 'Algorithm design and analysis'),
    ('CSC3400', 'Software Engineering', 4, 'Software engineering principles and practices'),
    ('CSC4410', 'Operating Systems & Concurrency', 4, 'Operating systems and concurrent programming'),
    ('CSC4899', 'Senior Project', 4, 'Capstone senior project'),
]

# Create courses and store them for prerequisite linking
course_objects = {}
for code, name, credits, desc in core_courses:
    course, created = Course.objects.get_or_create(
        course_code=code,
        defaults={
            'course_name': name,
            'credits': credits,
            'description': desc,
            'department': 'Computer Science'
        }
    )
    course_objects[code] = course
    print(f"  {code}: {name} (created={created})")

    # Add as major requirement
    DegreeRequirement.objects.get_or_create(
        major=csc_major,
        course=course,
        defaults={
            'requirement_type': 'REQUIRED',
            'credits_required': credits
        }
    )

# Add prerequisite relationships
prerequisites = [
    ('CSC2290', 'CSC2280'),  # OOP requires Intro to CS
    ('CSC3280', 'CSC2290'),  # Data Structures requires OOP
    ('CSC3310', 'CSC2290'),  # Computer Org requires OOP
    ('CSC3380', 'CSC3280'),  # Algorithms requires Data Structures
    ('CSC3400', 'CSC3280'),  # Software Engineering requires Data Structures
    ('CSC4410', 'CSC3280'),  # OS & Concurrency requires Data Structures
    ('CSC4899', 'CSC3400'),  # Senior Project requires Software Engineering
]

for course_code, prereq_code in prerequisites:
    course = course_objects[course_code]
    prereq_course = course_objects[prereq_code]

    Prerequisite.objects.get_or_create(
        course=course,
        prerequisite_course=prereq_course
    )
    print(f"  {prereq_code} is prerequisite for {course_code}")

print("\n✓ Database populated successfully!")
print(f"Created {len(course_objects)} courses")
print(f"Created {len(prerequisites)} prerequisite relationships")
