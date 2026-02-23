import os
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course
import PyPDF2


def extract_csc_courses_from_pdf(pdf_path):
    """Extract CSC course information from the catalog PDF"""

    # Open and read the PDF
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)

        # Extract text from pages 243-246 (where CSC courses are)
        full_text = ""
        for i in range(242, 246):  # Pages 243-246 (0-indexed)
            if i < len(pdf_reader.pages):
                full_text += pdf_reader.pages[i].extract_text()

        # Remove page headers/footers
        full_text = re.sub(r'FLORIDA SOUTHERN COLLEGE \d+', '', full_text)
        full_text = re.sub(r'UNDERGRADUATE COURSE DESCRIPTIONS \d+', '', full_text)

        # Split by CSC course codes
        courses = []

        # Pattern: CSC followed by course number, then course name on next line, then details
        pattern = r'CSC\s+(\d+)\s+([A-Z][A-Z\s\-/]+?)\n(.*?)(?=\nCSC\s+\d+|$)'

        matches = re.findall(pattern, full_text, re.DOTALL)

        for match in matches:
            course_number = match[0].strip()
            course_name = match[1].strip()
            details = match[2].strip()

            # Extract credits (looks like "Four hours" or "Two hours")
            credits_match = re.search(r'(Two|Three|Four)\s+hours?', details)
            if credits_match:
                credit_words = credits_match.group(1)
                credits = {'Two': 2, 'Three': 3, 'Four': 4}.get(credit_words, 4)
            else:
                credits = 4  # Default

            # Get everything after "hours."
            description = re.sub(r'^(Two|Three|Four)\s+hours?\.\s*', '', details)

            # Clean up line breaks
            description = ' '.join(description.split())

            # Remove page numbers
            description = re.sub(r'FLORIDA SOUTHERN COLLEGE \d+', '', description).strip()

            # If description is too short or empty, use a default
            if len(description) < 10:
                description = f"A {credits}-credit course in {course_name.title()}."

            # Trim at 500 characters if too long
            if len(description) > 500:
                description = description[:500].rsplit(' ', 1)[0] + '...'

            # Make sure it ends with a period
            if description and not description.endswith('.'):
                description += '.'

            # For now, set all to "Both"
            semester = 'Both'

            courses.append({
                'code': f'CSC{course_number}',
                'name': course_name,
                'credits': credits,
                'description': description,
                'semester': semester
            })

        return courses


def import_courses_to_database(courses):
    """Import courses into Django database"""

    for course_data in courses:
        course, created = Course.objects.update_or_create(
            course_code=course_data['code'],
            defaults={
                'course_name': course_data['name'],
                'credits': course_data['credits'],
                'description': course_data['description'],
                'department': 'Computer Science',
                'semester_offered': course_data['semester']
            }
        )

        if created:
            print(f"✓ Created: {course.course_code} - {course.course_name}")
        else:
            print(f"✓ Updated: {course.course_code} - {course.course_name}")


if __name__ == '__main__':
    pdf_path = 'fsc-catalog.pdf'

    print("Extracting CSC courses from PDF...")
    courses = extract_csc_courses_from_pdf(pdf_path)

    print(f"\nFound {len(courses)} CSC courses")
    print("\nImporting to database...\n")

    import_courses_to_database(courses)

    print("\n✅ Import complete!")
