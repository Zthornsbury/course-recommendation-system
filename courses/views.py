from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from courses.models import Student, Course, CompletedCourse, Prerequisite, DegreeRequirement, Major
from courses.recommender import CourseRecommender
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import io


def index(request):
    """Home page - student lookup or creation"""
    if request.method == 'POST':
        # Create new student
        student_id = request.POST.get('student_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        major_id = request.POST.get('major')
        graduation_date = request.POST.get('graduation_date')
        gpa = request.POST.get('gpa')

        # Get or create the major (CSC)
        major = Major.objects.get(id=major_id) if major_id else None

        # Create student
        student = Student.objects.create(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            major=major,
            expected_graduation=graduation_date if graduation_date else None,
            gpa=gpa if gpa else None
        )

        return redirect('dashboard', student_id=student_id)

    # Get all majors for the form
    majors = Major.objects.all()

    return render(request, 'courses/index.html', {'majors': majors})


def student_dashboard(request, student_id):
    """Student dashboard showing completed courses and recommendations"""
    student = get_object_or_404(Student, student_id=student_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_student':
            # Update student info
            gpa = request.POST.get('gpa')
            graduation_date = request.POST.get('graduation_date')

            if gpa:
                student.gpa = gpa
            if graduation_date:
                student.expected_graduation = graduation_date

            student.save()
            return redirect('dashboard', student_id=student_id)
        else:
            # Add completed course
            course_id = request.POST.get('course_id')
            grade = request.POST.get('grade')

            course = Course.objects.get(id=course_id)

            CompletedCourse.objects.create(
                student=student,
                course=course,
                grade=grade,
                completion_date=datetime.date.today()
            )

            return redirect('dashboard', student_id=student_id)

    # Get completed courses and all courses
    completed_courses = CompletedCourse.objects.filter(student=student).select_related('course')
    all_courses = Course.objects.all().order_by('course_code')

    # Get recommendations using the CourseRecommender
    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(max_credits_per_semester=18)

    context = {
        'student': student,
        'completed_courses': completed_courses,
        'all_courses': all_courses,
        'schedule': full_plan['schedule'],
        'total_semesters': full_plan['total_semesters'],
        'courses_remaining': full_plan['courses_remaining'],
    }

    return render(request, 'courses/dashboard.html', context)


def get_student(request):
    """API endpoint to look up student by ID"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')

        try:
            student = Student.objects.get(student_id=student_id)
            return redirect('dashboard', student_id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def course_catalog(request):
    """Display all available courses"""
    courses = Course.objects.all().order_by('course_code')

    context = {
        'courses': courses,
    }
    return render(request, 'courses/catalog.html', context)


def prerequisites(request):
    """Display prerequisite relationships"""
    prerequisites = Prerequisite.objects.all().select_related('course', 'prerequisite_course')

    # Group by course
    prereq_map = {}
    for prereq in prerequisites:
        if prereq.course.course_code not in prereq_map:
            prereq_map[prereq.course.course_code] = {
                'course': prereq.course,
                'prerequisites': []
            }
        prereq_map[prereq.course.course_code]['prerequisites'].append(prereq.prerequisite_course)

    context = {
        'prereq_map': prereq_map,
    }

    return render(request, 'courses/prerequisites.html', context)


def plan_schedule(request):
    """Plan My Schedule page - student lookup"""
    majors = Major.objects.all()

    context = {
        'majors': majors,
    }
    return render(request, 'courses/plan_schedule.html', context)


def download_schedule_pdf(request, student_id):
    """Generate and download student schedule as PDF"""
    student = get_object_or_404(Student, student_id=student_id)

    # Get the schedule data
    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(max_credits_per_semester=18)

    # Create the PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#3498db'),
        spaceAfter=12,
    )

    # Title
    title = Paragraph("DegreePath - Graduation Schedule", title_style)
    elements.append(title)

    # Student info
    student_info = [
        ['Student:', f"{student.first_name} {student.last_name}"],
        ['Student ID:', student.student_id],
        ['Major:', student.major.name],
        ['GPA:', str(student.gpa) if student.gpa else 'Not set'],
        ['Total Semesters:', str(full_plan['total_semesters'])],
    ]

    info_table = Table(student_info, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Schedule by semester
    for semester_plan in full_plan['schedule']:
        # Semester heading
        semester_heading = Paragraph(
            f"{semester_plan['semester']} — {semester_plan['total_credits']} credits",
            heading_style
        )
        elements.append(semester_heading)

        # Courses table
        course_data = [['Course Code', 'Course Name', 'Credits']]
        for course in semester_plan['courses']:
            course_data.append([
                course.course_code,
                course.course_name[:40],  # Truncate long names
                str(course.credits)
            ])

        course_table = Table(course_data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        course_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        elements.append(course_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Return as download
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DegreePath_Schedule_{student.student_id}.pdf"'

    return response
