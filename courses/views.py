from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from courses.models import Student, Course, CompletedCourse
from courses.recommender import CourseRecommender
import datetime
from django.shortcuts import redirect


def index(request):
    """Home page - student lookup"""
    return render(request, 'courses/index.html')


def student_dashboard(request, student_id):
    """Display student info and recommendations"""
    student = get_object_or_404(Student, student_id=student_id)

    # Get completed courses
    completed_courses = list(CompletedCourse.objects.filter(student=student).select_related('course'))

    # Get recommendations
    recommender = CourseRecommender(student)
    recommendations = recommender.get_recommendations(max_credits=18)
    recommended_courses = recommendations['recommended']
    total_credits = recommendations['total_credits']
    remaining_courses = recommendations['remaining_to_complete']

    # Handle form submission
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        grade = request.POST.get('grade')

        if course_id and grade:
            course = Course.objects.get(id=course_id)
            CompletedCourse.objects.get_or_create(
                student=student,
                course=course,
                defaults={
                    'semester': 'Current',
                    'grade': grade,
                    'date_completed': datetime.date.today()
                }
            )
            return redirect('dashboard', student_id=student_id)

    # Get all available courses
    all_courses = Course.objects.all()

    context = {
        'student': student,
        'completed_courses': completed_courses,
        'recommended_courses': recommended_courses,
        'total_credits': total_credits,
        'remaining_courses': remaining_courses,
        'all_courses': all_courses,
    }

    return render(request, 'courses/dashboard.html', context)


def get_student(request):
    """AJAX endpoint to get student by ID"""
    student_id = request.GET.get('student_id', '')

    try:
        student = Student.objects.get(student_id=student_id)
        return JsonResponse({
            'found': True,
            'student_id': student.student_id,
            'name': f"{student.first_name} {student.last_name}",
            'major': student.major.name if student.major else 'No major',
        })
    except Student.DoesNotExist:
        return JsonResponse({
            'found': False,
            'message': 'Student not found'
        })