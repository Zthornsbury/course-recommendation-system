import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course, DegreeRequirement, Major

# ============================================================
# WRIGHT Foundation course descriptions
# Used to update the database with proper descriptions
# ============================================================
WRIGHT_DESCRIPTIONS = {
    'ART1100': 'Explores the history and theory of art and architecture from ancient civilizations to the modern era. Develops visual literacy and critical analysis skills through study of major works and movements.',
    'BIO1005': 'An introduction to current topics in biology including cell biology, genetics, evolution, and ecology. Emphasizes scientific thinking and real-world biological applications.',
    'BIO1050': 'Covers fundamental biological concepts including cell structure, metabolism, genetics, and the diversity of life. Laboratory component reinforces lecture material.',
    'CHE1050': 'Introduction to the principles of chemistry including atomic structure, chemical bonding, reactions, and stoichiometry. Includes laboratory work to develop experimental skills.',
    'COM1500': 'Develops public speaking and oral communication skills through prepared and impromptu speeches, group discussion, and formal presentations. Emphasizes clarity, organization, and audience awareness.',
    'DPT2000': 'Focuses on building personal resilience, stress management, and life skills needed to thrive academically and professionally. Topics include goal setting, wellness, and strategic planning.',
    'ENG1005': 'Develops written communication skills through analysis and composition. Focuses on clarity, argumentation, research, and academic writing conventions across a variety of genres.',
    'HIS1300': 'Survey of modern world history from the early modern period to the present. Examines political, social, economic, and cultural developments that shaped the contemporary world.',
    'MAT2022': 'Introduction to statistical methods including data collection, descriptive statistics, probability, and inferential statistics. Emphasizes real-world data analysis and interpretation.',
    'MAT2100': 'An introduction to discrete mathematics. Topics include logic, set theory, basic proofs, mathematical induction and recursion, counting principles and probability.',
    'MUS1101': 'Participation in the college choir ensemble. Develops vocal technique, music reading, and performance skills through rehearsal and public concert performance.',
    'PHI2304': 'Examines major ethical theories and applies them to contemporary moral issues. Topics include justice, rights, virtue ethics, and moral reasoning in personal and professional contexts.',
    'PSY1106': 'Introduction to psychological principles and their application to human behavior in social contexts. Topics include perception, motivation, learning, and social influence.',
    'REL2314': 'Examination of Christian ethical principles and their application to contemporary moral and social issues. Explores the relationship between faith, reason, and ethical decision-making.',
    'SOC1100': 'Introduction to sociological concepts and methods. Examines social institutions, culture, stratification, inequality, and social change in modern society.',
}

# ============================================================
# WRIGHT Foundation course data
# ============================================================
wright_courses = [
    # A. Written Communication
    {'code': 'ENG1005', 'name': 'Writing About Topics', 'credits': 4, 'dept': 'English', 'semester': 'Both'},

    # B. Oral Communication
    {'code': 'COM1500', 'name': 'Speak for Success', 'credits': 4, 'dept': 'Communication', 'semester': 'Both'},

    # R: Resilience
    {'code': 'DPT2000', 'name': 'Strategic Resilience: Building Strength for Life', 'credits': 2,
     'dept': 'General Education', 'semester': 'Both'},

    # I: Investigating Connections in Social/Behavioral Sciences
    {'code': 'PSY1106', 'name': 'Psychology and the Social World', 'credits': 4, 'dept': 'Psychology',
     'semester': 'Both'},
    {'code': 'SOC1100', 'name': 'Introduction to Sociology', 'credits': 4, 'dept': 'Sociology', 'semester': 'Both'},

    # G: Global Perspectives
    {'code': 'HIS1300', 'name': 'The Modern World', 'credits': 4, 'dept': 'History', 'semester': 'Both'},

    # H: Humanities
    {'code': 'PHI2304', 'name': 'Ethics', 'credits': 4, 'dept': 'Philosophy', 'semester': 'Both'},
    {'code': 'REL2314', 'name': 'Christian Ethics', 'credits': 4, 'dept': 'Religion', 'semester': 'Both'},

    # H: Fine Arts
    {'code': 'ART1100', 'name': 'History of Art and Architecture', 'credits': 4, 'dept': 'Art', 'semester': 'Both'},
    {'code': 'MUS1101', 'name': 'Chamber Singers', 'credits': 4, 'dept': 'Music', 'semester': 'Both'},

    # T: Natural Science
    {'code': 'BIO1005', 'name': 'Topics in Biology', 'credits': 4, 'dept': 'Biology', 'semester': 'Both'},
    {'code': 'BIO1050', 'name': 'Biology I: Biological Essentials', 'credits': 4, 'dept': 'Biology',
     'semester': 'Both'},
    {'code': 'CHE1050', 'name': 'Principles of Chemistry I', 'credits': 4, 'dept': 'Chemistry', 'semester': 'Both'},

    # T: Mathematics
    {'code': 'MAT2022', 'name': 'Elementary Statistics', 'credits': 4, 'dept': 'Mathematics', 'semester': 'Both'},
    {'code': 'MAT2100', 'name': 'Discrete Mathematics', 'credits': 4, 'dept': 'Mathematics', 'semester': 'Both'},
]


def import_wright_courses():
    print("=" * 60)
    print("IMPORTING WRIGHT FOUNDATION COURSES")
    print("=" * 60 + "\n")

    for course_data in wright_courses:
        # Use description from WRIGHT_DESCRIPTIONS if available
        description = WRIGHT_DESCRIPTIONS.get(
            course_data['code'],
            f"WRIGHT Foundation requirement in {course_data['dept']}."
        )

        course, created = Course.objects.update_or_create(
            course_code=course_data['code'],
            defaults={
                'course_name': course_data['name'],
                'credits': course_data['credits'],
                'description': description,
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