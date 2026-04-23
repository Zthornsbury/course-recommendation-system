# This file contains all the view functions for the DegreePath
# course recommendation system. Each view handles a specific
# page or action in the application.
#
# Views in this file:
#   - login_view         → /login/
#   - logout_view        → /logout/
#   - register_view      → /register/
#   - index              → / (home page)
#   - student_dashboard  → /dashboard/<student_id>/
#   - delete_completed_course → /dashboard/<student_id>/delete/<course_id>/
#   - schedule           → /schedule/
#   - get_student        → /get-student/ (API)
#   - course_catalog     → /catalog/
#   - prerequisites      → /prerequisites/
#   - plan_schedule      → /plan/
#   - download_schedule_pdf → /schedule/download/<student_id>/

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from courses.recommender import CourseRecommender
import datetime
import traceback
import random
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import io
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from courses.models import (
    Student, Course, CompletedCourse, Prerequisite,
    DegreeRequirement, Major, StudentPreference, PinnedCourse, StudentElective
)
from django.contrib.auth.models import User
from courses.course_config import (
    COURSE_PREREQUISITES,
    CS_CORE_REQUIRED,
    CS_CONCENTRATION_AI,
    CS_CONCENTRATION_WEB,
    CS_CONCENTRATION_CYBER
)



# HELPER FUNCTIONS
# These are utility functions used across multiple views.


def semester_to_date(semester_str):
    """
    Convert a semester string like 'Spring-2028' or 'Fall-2028'
    into a Python datetime.date object.

    Spring → May 1st of that year
    Fall   → December 1st of that year

    Returns None if the string is empty or malformed.
    Used when saving a student's expected graduation date.
    """
    if not semester_str:
        return None
    parts = semester_str.split('-')
    if len(parts) == 2:
        sem, year = parts[0], int(parts[1])
        if sem == 'Spring':
            return datetime.date(year, 5, 1)
        elif sem == 'Fall':
            return datetime.date(year, 12, 1)
    return None


def date_to_semester(date_obj):
    """
    Convert a Python date object into a human-readable semester string
    like 'Spring 2028' or 'Fall 2028'.

    Month 1-7  → Spring (semester ends in May)
    Month 8-12 → Fall   (semester ends in December)

    Returns None if date_obj is None.
    Used to display graduation dates in a friendly format.
    """
    if not date_obj:
        return None
    if date_obj.month <= 7:
        return f"Spring {date_obj.year}"
    else:
        return f"Fall {date_obj.year}"


def get_elective_requirement(student):
    """
    Return the number of elective credits a student must complete.

    Students WITH a concentration only need 8 elective credits
    because their concentration courses fill the rest of the requirement.

    Students WITHOUT a concentration need 20 elective credits
    because they have more open slots to fill with general electives.
    """
    return 8 if student.concentration else 20



# LOGIN VIEW
# URL: /login/

def login_view(request):
    """
    Displays the login page and authenticates the user on form submission.

    GET:  Renders the login form. If the user is already logged in,
          redirects them straight to their dashboard instead.

    POST: Reads username (student ID) and password from the form.
          If credentials are valid, logs the user in and redirects
          to their dashboard. If the user exists but has no linked
          Student profile, logs them out and shows an error.
    """

    # If user is already authenticated, skip the login page entirely
    if request.user.is_authenticated:
        try:
            return redirect('dashboard', student_id=request.user.student.student_id)
        except:
            pass  # If no student profile linked, fall through to show login

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Django's built-in authenticate checks username + password against DB
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                # Redirect to the student's dashboard using their student_id
                return redirect('dashboard', student_id=user.student.student_id)
            except:
                # Edge case: user account exists but no Student record linked to it
                logout(request)
                return render(request, 'courses/login.html', {
                    'error': 'No student profile found for this account. Please register a new account.'
                })

    # GET request — just show the login form with no error
    return render(request, 'courses/login.html')



# LOGOUT VIEW
def logout_view(request):
    """
    Logs the current user out using Django's built-in logout function,
    then redirects them to the login page.
    """
    logout(request)
    return redirect('login')


# REGISTER VIEW
# URL: /register/
def register_view(request):
    """
    Handles new student account creation.

    GET:  Renders the registration form with a list of available majors
          and a range of graduation years to choose from.

    POST: Validates all form fields, then creates a Django User account
          and a linked Student profile. Logs the new student in immediately
          after successful registration and redirects to their dashboard.

    Validation checks (in order):
    1. Student ID must be numeric only
    2. Passwords must match
    3. Password must meet complexity requirements:
       - At least 8 characters
       - At least one uppercase letter
       - At least one lowercase letter
       - At least one number
       - At least one special character
    4. Username (Student ID) must not already exist in the User table
    5. Student ID must not already exist in the Student table
    """

    current_year = datetime.date.today().year
    # Offer graduation year options from now through the next 8 years
    graduation_years = range(current_year, current_year + 8)

    if request.method == 'POST':
        username = request.POST.get('username')

        # ── Validation 1: Student ID must be numeric ──────────
        if not username.isdigit():
            return render(request, 'courses/register.html', {
                'error': 'Student ID must contain numbers only.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        major_id = request.POST.get('major')
        graduation_semester = request.POST.get('graduation_semester', '')
        gpa = request.POST.get('gpa')
        concentration = request.POST.get('concentration', '')

        # ── Validation 2: Passwords must match ────────────────
        if password != confirm_password:
            return render(request, 'courses/register.html', {
                'error': 'Passwords do not match.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        # ── Validation 3: Password complexity ─────────────────
        # Collect ALL failures so the student sees them all at once
        errors = []
        if len(password) < 8:
            errors.append('At least 8 characters')
        if not any(c.isupper() for c in password):
            errors.append('At least one uppercase letter')
        if not any(c.islower() for c in password):
            errors.append('At least one lowercase letter')
        if not any(c.isdigit() for c in password):
            errors.append('At least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            errors.append('At least one special character (!@#$%^&* etc.)')

        if errors:
            return render(request, 'courses/register.html', {
                'error': 'Password must contain: ' + ', '.join(errors),
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        # ── Validation 4: Username must be unique ─────────────
        if User.objects.filter(username=username).exists():
            return render(request, 'courses/register.html', {
                'error': 'Username already exists.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        # ── Validation 5: Student ID must be unique ───────────
        if Student.objects.filter(student_id=username).exists():
            return render(request, 'courses/register.html', {
                'error': 'A student with that ID already exists.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        # ── All checks passed — create accounts ───────────────
        # create_user handles password hashing automatically
        user = User.objects.create_user(username=username, password=password)

        # Look up the selected major, or leave it as None if not chosen
        major = Major.objects.get(id=major_id) if major_id else None

        # Convert the graduation semester string to a date object for DB storage
        graduation_date = semester_to_date(graduation_semester)

        # Create the Student profile linked to the Django User account
        student = Student.objects.create(
            user=user,
            student_id=username,
            first_name=first_name,
            last_name=last_name,
            major=major,
            concentration=concentration,
            expected_graduation=graduation_date,
            gpa=gpa if gpa else None,  # Store None if GPA field was left blank
        )

        # Log the student in right away — no need to log in again after registering
        login(request, user)
        return redirect('dashboard', student_id=student.student_id)

    # GET request — render the registration form
    majors = Major.objects.all()
    return render(request, 'courses/register.html', {
        'majors': majors,
        'graduation_years': graduation_years,
    })



# INDEX / HOME VIEW

@login_required(login_url='/login/')
def index(request):
    """
    Home page — used for student lookup or manual student creation
    (mainly for admin use). Most users go straight to the dashboard
    after logging in so this page is rarely hit directly.

    POST: Finds or creates a student record by student_id and
          redirects to their dashboard.

    GET:  Renders the home page with a list of majors.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        major_id = request.POST.get('major')
        graduation_date = request.POST.get('graduation_date')
        gpa = request.POST.get('gpa')

        major = Major.objects.get(id=major_id) if major_id else None

        # get_or_create either finds the existing student or creates a new one
        student, created = Student.objects.get_or_create(
            student_id=student_id,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'major': major,
                'expected_graduation': graduation_date if graduation_date else None,
                'gpa': gpa if gpa else None,
            }
        )
        return redirect('dashboard', student_id=student_id)

    majors = Major.objects.all()
    return render(request, 'courses/index.html', {'majors': majors})



# STUDENT DASHBOARD VIEW

@login_required(login_url='/login/')
def student_dashboard(request, student_id):
    """
    Main student dashboard page. Shows the student's academic progress,
    completed courses, estimated graduation date, and any GPA warnings.

    GET:  Loads the dashboard with all stats and course information.
    POST: Handles two different form actions based on the 'action' field:

      action = 'update_student':
        Updates the student's GPA, expected graduation, and concentration.
        Redirects back to the dashboard after saving.

      action = (anything else / default):
        Adds a course to the student's completed courses list.
        Before adding, validates that all prerequisites have been met.
        If prerequisites are missing, re-renders the dashboard with an error.
        If prerequisites are met, records the completion and redirects.
    """
    student = get_object_or_404(Student, student_id=student_id)

    current_year = datetime.date.today().year
    graduation_years = range(current_year, current_year + 8)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Action: Update student profile ────────────────────
        if action == 'update_student':
            gpa = request.POST.get('gpa')
            graduation_semester = request.POST.get('graduation_semester', '')
            concentration = request.POST.get('concentration', '')

            if gpa:
                student.gpa = gpa

            # Convert the semester dropdown value to a date for storage
            graduation_date = semester_to_date(graduation_semester)
            if graduation_date:
                student.expected_graduation = graduation_date

            student.concentration = concentration
            student.save()
            return redirect('dashboard', student_id=student_id)

        # ── Action: Add a completed course ────────────────────
        else:
            course_id = request.POST.get('course_id')
            grade = request.POST.get('grade')
            course = Course.objects.get(id=course_id)

            # Get all course IDs the student has already completed
            completed_ids = set(
                CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
            )

            # Check prerequisites — try the database first
            required_prereqs = set(
                Prerequisite.objects.filter(course=course).values_list('prerequisite_course_id', flat=True)
            )

            # If no DB prerequisites found, fall back to course_config.py
            if not required_prereqs:
                config_codes = COURSE_PREREQUISITES.get(course.course_code, [])
                if config_codes:
                    required_prereqs = set(
                        Course.objects.filter(course_code__in=config_codes).values_list('id', flat=True)
                    )

            # If the student hasn't completed all prerequisites, show an error
            if not required_prereqs.issubset(completed_ids):
                missing = Course.objects.filter(
                    id__in=required_prereqs - completed_ids
                ).values_list('course_code', flat=True)

                # Rebuild the full dashboard context to re-render with the error
                completed_courses = CompletedCourse.objects.filter(student=student).select_related('course')
                completed_ids_set = set(
                    CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
                )

                all_courses = Course.objects.exclude(id__in=completed_ids_set).order_by('course_code')
                preferences, _ = StudentPreference.objects.get_or_create(student=student)
                # collects students preferences and get_full_schedule in recommender.py figures out what goes where based on prerequisites,credit limit, priority
                pinned_dict = {}
                for pinned in PinnedCourse.objects.filter(preference=preferences):
                    pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

                recommender = CourseRecommender(student)
                full_plan = recommender.get_full_schedule(
                    max_credits_per_semester=preferences.target_credits_per_semester,
                    pinned_courses=pinned_dict,
                    priority=preferences.priority
                )

                credits_completed = sum(cc.course.credits for cc in completed_courses)
                total_credits_required = student.major.total_credits_required if student.major else 124
                progress_percent = min(int((credits_completed / total_credits_required) * 100), 100)

                # Determine GPA warning level for the warning banner
                gpa_warning = None
                if student.gpa:
                    gpa = float(student.gpa)
                    if gpa < 2.0:
                        gpa_warning = 'probation'
                    elif gpa < 3.0:
                        gpa_warning = 'at_risk'

                # Determine if the credit cap has been reduced due to low GPA
                credit_reduction_notice = None
                if student.gpa:
                    gpa = float(student.gpa)
                    if gpa < 2.5:
                        credit_reduction_notice = f'Your GPA of {student.gpa} is below 2.5. Your schedule has been limited to 9 credits per semester.'
                    elif gpa < 3.0:
                        credit_reduction_notice = f'Your GPA of {student.gpa} is below 3.0. Your schedule has been limited to 12 credits per semester.'

                context = {
                    'student': student,
                    'completed_courses': completed_courses,
                    'all_courses': all_courses,
                    'total_semesters': full_plan['total_semesters'],
                    'courses_remaining': full_plan['courses_remaining'],
                    'is_behind': False,
                    'realistic_graduation': None,
                    'realistic_graduation_semester': None,
                    'expected_graduation_semester': date_to_semester(student.expected_graduation),
                    'credits_completed': credits_completed,
                    'total_credits_required': total_credits_required,
                    'progress_percent': progress_percent,
                    'gpa_warning': gpa_warning,
                    'credit_reduction_notice': credit_reduction_notice,
                    'graduation_years': graduation_years,
                    'prereq_error': f"Cannot add {course.course_code} — complete these first: {', '.join(missing)}",
                }
                return render(request, 'courses/dashboard.html', context)

            # Prerequisites met — record the completed course in the DB
            CompletedCourse.objects.create(
                student=student,
                course=course,
                grade=grade,
                completion_date=datetime.date.today()
            )
            return redirect('dashboard', student_id=student_id)

    # ── GET REQUEST — build dashboard context ──────────────────

    # Load all courses the student has completed
    completed_courses = CompletedCourse.objects.filter(student=student).select_related('course')
    completed_ids = set(
        CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
    )
    # All courses the student hasn't completed yet (for the "add course" dropdown)
    all_courses = Course.objects.exclude(id__in=completed_ids).order_by('course_code')

    # Load saved preferences and pinned course assignments
    preferences, _ = StudentPreference.objects.get_or_create(student=student)
    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    # Run the recommender to get stats like total semesters and courses remaining
    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    # ── Graduation on-track check ──────────────────────────────
    # Compare the realistic graduation (based on courses left) to the
    # student's expected graduation. Flag if they're behind.
    is_behind = False
    realistic_graduation = None
    realistic_graduation_semester = None
    expected_graduation_semester = date_to_semester(student.expected_graduation)

    if student.expected_graduation:
        remaining_credits = sum(
            semester['total_credits'] for semester in full_plan['schedule']
        )
        credits_per_semester = 18
        # Ceiling division to get number of semesters needed
        semesters_needed = -(-remaining_credits // credits_per_semester)
        # Each semester is roughly 6 months
        raw_date = datetime.date.today() + relativedelta(months=semesters_needed * 6)

        month = raw_date.month
        year = raw_date.year
        if month <= 7:
            realistic_graduation_semester = f"Spring {year}"
            realistic_graduation = datetime.date(year, 5, 1)
        else:
            realistic_graduation_semester = f"Fall {year}"
            realistic_graduation = datetime.date(year, 12, 1)

        expected = student.expected_graduation
        if isinstance(expected, str):
            expected = datetime.datetime.strptime(expected, "%Y-%m-%d").date()

        # Student is behind if realistic graduation is after their expected date
        is_behind = realistic_graduation > expected

    # ── Progress bar calculation ───────────────────────────────
    credits_completed = sum(cc.course.credits for cc in completed_courses)
    total_credits_required = student.major.total_credits_required if student.major else 124
    # Cap at 100% so the bar doesn't overflow
    progress_percent = min(int((credits_completed / total_credits_required) * 100), 100)

    # ── GPA warning banner ─────────────────────────────────────
    # 'probation' → GPA below 2.0 (academic probation territory)
    # 'at_risk'   → GPA below 3.0 (struggling but not on probation)
    gpa_warning = None
    if student.gpa:
        gpa = float(student.gpa)
        if gpa < 2.0:
            gpa_warning = 'probation'
        elif gpa < 3.0:
            gpa_warning = 'at_risk'

    # ── Credit reduction notice ────────────────────────────────
    # Shown when the recommender has auto-reduced the per-semester credit cap
    # due to the student's low GPA (handled inside the recommender itself)
    credit_reduction_notice = None
    if student.gpa:
        gpa = float(student.gpa)
        if gpa < 2.5:
            credit_reduction_notice = f'Your GPA of {student.gpa} is below 2.5. Your schedule has been limited to 9 credits per semester.'
        elif gpa < 3.0:
            credit_reduction_notice = f'Your GPA of {student.gpa} is below 3.0. Your schedule has been limited to 12 credits per semester.'

    context = {
        'student': student,
        'completed_courses': completed_courses,
        'all_courses': all_courses,
        'total_semesters': full_plan['total_semesters'],
        'courses_remaining': full_plan['courses_remaining'],
        'is_behind': is_behind,
        'realistic_graduation': realistic_graduation,
        'realistic_graduation_semester': realistic_graduation_semester,
        'expected_graduation_semester': expected_graduation_semester,
        'credits_completed': credits_completed,
        'total_credits_required': total_credits_required,
        'progress_percent': progress_percent,
        'gpa_warning': gpa_warning,
        'credit_reduction_notice': credit_reduction_notice,
        'graduation_years': graduation_years,
    }

    return render(request, 'courses/dashboard.html', context)


# ============================================================
# DELETE COMPLETED COURSE VIEW
# URL: /dashboard/<student_id>/delete/<course_id>/
# ============================================================
@login_required(login_url='/login/')
def delete_completed_course(request, student_id, course_id):
    """
    Removes a course from the student's completed courses list.

    Security check: verifies the logged-in user owns this student profile
    before allowing deletion. If they don't match, redirects back to
    the dashboard without deleting anything.
    """
    student = get_object_or_404(Student, student_id=student_id)

    try:
        # Make sure the logged-in user is the owner of this student profile
        if request.user.student != student:
            return redirect('dashboard', student_id=student_id)
    except:
        return redirect('dashboard', student_id=student_id)

    CompletedCourse.objects.filter(student=student, course_id=course_id).delete()
    return redirect('dashboard', student_id=student_id)


# SCHEDULE VIEW
@login_required(login_url='/login/')
def schedule(request):
    """
    Displays the student's generated graduation schedule.

    Loads the student's saved preferences (credit target, priority, pinned courses)
    and runs the CourseRecommender to generate the full semester-by-semester plan.

    Also reads an elective auto-fill notice from the session if one was stored
    by the plan_schedule view after saving preferences. The notice is shown once
    at the top of the schedule page and then cleared from the session so it
    doesn't appear again on refresh.
    """
    try:
        student = request.user.student
    except:
        # If the logged-in user has no student profile, send them to login
        return redirect('login')

    preferences, _ = StudentPreference.objects.get_or_create(student=student)

    # Rebuild the pinned courses dictionary for the recommender
    # Format: {'Semester 1': [course_id, ...], 'Semester 2': [...], ...}
    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    # Run the recommender to generate the full schedule
    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    # Read the elective auto-fill notice from the session.
    # pop() removes it after reading so it only shows once —
    # refreshing the page won't show it again.
    elective_notice = request.session.pop('elective_notice', None)

    context = {
        'student': student,
        'schedule': full_plan['schedule'],           # List of semester dicts
        'total_semesters': full_plan['total_semesters'],
        'courses_remaining': full_plan['courses_remaining'],
        'target_credits': preferences.target_credits_per_semester,
        'elective_notice': elective_notice,          # May be None if no auto-fill happened
    }
    return render(request, 'courses/schedule.html', context)


# GET STUDENT API ENDPOINT
def get_student(request):
    """
    Simple API endpoint that looks up a student by their student_id.
    Used for AJAX lookups or form submissions that need to verify a student exists.

    POST: Returns a redirect to the student's dashboard if found,
          or a 404 JSON error if not found.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id)
            return redirect('dashboard', student_id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)



# COURSE CATALOG VIEW
@login_required(login_url='/login/')
def course_catalog(request):
    """
    Displays all courses in the system split into two sections:
    - Computer Science Major Courses (CS department)
    - General Education & Elective Courses (all other departments)

    Deduplicates the second list by both course code and course name
    to prevent the same course appearing in both sections if it
    happens to exist in multiple departments.
    """
    # All CS department courses sorted by code
    cs_courses = Course.objects.filter(department='Computer Science').order_by('course_code')

    # Build sets for fast deduplication lookups
    cs_codes = set(cs_courses.values_list('course_code', flat=True))
    cs_names = set(name.lower().strip() for name in cs_courses.values_list('course_name', flat=True))

    # All non-CS courses, filtered to remove any duplicates of CS courses
    other_courses = Course.objects.exclude(department='Computer Science').order_by('department', 'course_code')
    other_courses = [
        c for c in other_courses
        if c.course_code not in cs_codes and c.course_name.lower().strip() not in cs_names
    ]

    return render(request, 'courses/catalog.html', {
        'cs_courses': cs_courses,
        'other_courses': other_courses,
    })



# PREREQUISITES VIEW
@login_required(login_url='/login/')
def prerequisites(request):
    """
    Displays a map of all course prerequisites.

    For each course, checks the database first for prerequisite records.
    If none are found in the DB, falls back to course_config.py which
    has the prerequisite chains defined as a Python dictionary.

    This dual-source approach means the page works correctly even if
    prerequisites haven't been imported into the database yet.
    """
    all_courses = Course.objects.all().order_by('course_code')
    prereq_map = {}

    for course in all_courses:
        # Try to find prerequisites in the Prerequisite table first
        db_prereqs = Prerequisite.objects.filter(course=course).select_related('prerequisite_course')

        if db_prereqs.exists():
            prereq_map[course.course_code] = {
                'course': course,
                'prerequisites': [p.prerequisite_course for p in db_prereqs]
            }
        else:
            # Fall back to course_config.py COURSE_PREREQUISITES dictionary
            config_codes = COURSE_PREREQUISITES.get(course.course_code, [])
            if config_codes:
                config_prereq_courses = Course.objects.filter(course_code__in=config_codes)
                prereq_map[course.course_code] = {
                    'course': course,
                    'prerequisites': list(config_prereq_courses)
                }
            # If no prerequisites found anywhere, the course is just not added to the map

    return render(request, 'courses/prerequisites.html', {'prereq_map': prereq_map})



# PLAN SCHEDULE VIEW
@login_required(login_url='/login/')
def plan_schedule(request):
    """
    The Plan My Schedule page. This is where students configure their
    schedule preferences before generating their graduation plan.

    Features on this page:
    - Target credits per semester slider (9-18)
    - Course priority selector (Balanced / Gen Ed First / CS First)
    - Elective selector (student picks courses to include)
    - Drag-and-drop course pinning to specific semesters
    - Save & Generate Schedule button

    GET:
      Loads the current preferences, remaining required courses,
      and available electives. Shows a warning if the student hasn't
      selected enough elective credits yet.

    POST (action = 'save_preferences'):
      Step 1: Save the credit target and priority preference
      Step 2: Save manually selected electives
      Step 3: Auto-fill electives if the student is short of the requirement
      Step 4: Save pinned course assignments to specific semesters
      Step 5: Store any auto-fill notice in the session for display on schedule page
      Step 6: ALWAYS redirect to the schedule page

      Note: The old version re-rendered the plan page when auto-fill happened,
      which broke the Generate button. Now we always redirect to /schedule/.
    """
    majors = Major.objects.all()

    try:
        student = request.user.student
        student_id = student.student_id
    except:
        student = None
        student_id = None

    # Initialize all template variables to safe defaults
    preferences = None
    pinned_courses = []
    all_remaining = []
    all_electives = []
    selected_elective_ids = set()
    senior_project_id = None
    elective_notice = None      # Shown after electives are auto-filled
    elective_warning = None     # Shown when student hasn't selected enough electives

    if student:
        # Load or create preference record for this student
        preferences, _ = StudentPreference.objects.get_or_create(student=student)
        pinned_courses = PinnedCourse.objects.filter(preference=preferences).select_related('course')

        # IDs of all courses the student has already completed
        completed_ids = set(
            CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
        )

        # Build the required course pool from the student's degree requirements
        required_ids = set(
            DegreeRequirement.objects.filter(major=student.major).values_list('course_id', flat=True)
        )

        # Add concentration courses to the required pool if student has one
        if student.concentration:
            concentration_map = {
                'AI': CS_CONCENTRATION_AI,
                'WEB': CS_CONCENTRATION_WEB,
                'CYBER': CS_CONCENTRATION_CYBER,
            }
            concentration_codes = concentration_map.get(student.concentration, [])
            if concentration_codes:
                concentration_ids = set(
                    Course.objects.filter(
                        course_code__in=concentration_codes
                    ).values_list('id', flat=True)
                )
                required_ids = required_ids | concentration_ids

        # Add any electives the student has already selected on this page
        selected_elective_ids = set(
            StudentElective.objects.filter(student=student).values_list('course_id', flat=True)
        )
        required_ids = required_ids | selected_elective_ids

        # Senior Project (CSC4899) is handled specially by the recommender —
        # it's always placed in the last Fall semester, so we exclude it here
        senior_project = Course.objects.filter(course_code='CSC4899').first()
        senior_project_id = senior_project.id if senior_project else None
        exclude_ids = {senior_project_id} if senior_project_id else set()

        # Courses still required but not yet completed (shown in the pinning area)
        all_remaining = Course.objects.filter(
            id__in=required_ids - completed_ids
        ).exclude(id__in=exclude_ids).order_by('course_code')

        # All elective options: not required, not completed, sorted by department
        all_electives = Course.objects.exclude(
            id__in=required_ids
        ).exclude(
            id__in=completed_ids
        ).order_by('department', 'course_code')

        # ── Elective credit requirement check ──────────────────
        # Calculate how many elective credits the student still needs
        elective_credits_required = get_elective_requirement(student)

        # Credits from already-completed courses that weren't required
        # (i.e. electives the student already took)
        completed_elective_credits = sum(
            cc.course.credits for cc in CompletedCourse.objects.filter(
                student=student
            ).select_related('course')
            if cc.course.id not in required_ids
        )

        # Credits from electives the student has selected (but not yet completed)
        selected_elective_credits = sum(
            Course.objects.filter(id__in=selected_elective_ids).values_list('credits', flat=True)
        )

        total_elective_credits = completed_elective_credits + selected_elective_credits
        elective_credits_still_needed = max(0, elective_credits_required - total_elective_credits)

        # Show a warning banner if the student still needs more electives
        if elective_credits_still_needed > 0:
            elective_warning = {
                'required': elective_credits_required,
                'selected': total_elective_credits,
                'needed': elective_credits_still_needed,
                'concentration': student.concentration,
            }

    if request.method == 'POST' and student:
        action = request.POST.get('action')

        if action == 'save_preferences':
            try:
                # ── Step 1: Save credit target ─────────────────
                # Enforce a minimum of 9 credits per semester regardless
                # of what value the slider was set to
                target_credits = request.POST.get('target_credits')
                if target_credits:
                    preferences.target_credits_per_semester = max(9, int(target_credits))

                # ── Step 2: Save priority preference ───────────
                # BALANCED / GEN_ED_FIRST / CS_FIRST
                priority = request.POST.get('priority', 'BALANCED')
                preferences.priority = priority
                preferences.save()

                # ── Step 3: Save manually selected electives ────
                # Clear all previous selections first, then save the new ones.
                # The form sends back the full list of checked electives.
                StudentElective.objects.filter(student=student).delete()
                selected_electives = request.POST.getlist('selected_electives')

                for course_id in selected_electives:
                    try:
                        course = Course.objects.get(id=course_id)
                        StudentElective.objects.get_or_create(student=student, course=course)
                    except Course.DoesNotExist:
                        pass  # Skip invalid IDs silently

                # ── Step 4: Auto-fill electives if short ────────
                # After saving manual selections, recalculate how many
                # elective credits the student still needs. If they're
                # short, randomly pick courses to fill the gap.
                elective_credits_required = get_elective_requirement(student)

                # Recalculate completed and required IDs fresh after saves
                completed_ids_now = set(
                    CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
                )
                required_ids_now = set(
                    DegreeRequirement.objects.filter(major=student.major).values_list('course_id', flat=True)
                )

                # Re-add concentration courses to the required pool
                if student.concentration:
                    concentration_map = {
                        'AI': CS_CONCENTRATION_AI,
                        'WEB': CS_CONCENTRATION_WEB,
                        'CYBER': CS_CONCENTRATION_CYBER,
                    }
                    conc_codes = concentration_map.get(student.concentration, [])
                    if conc_codes:
                        conc_ids = set(
                            Course.objects.filter(course_code__in=conc_codes).values_list('id', flat=True)
                        )
                        required_ids_now = required_ids_now | conc_ids

                # Current elective selections after manual save
                current_elective_ids = set(
                    StudentElective.objects.filter(student=student).values_list('course_id', flat=True)
                )

                # Credits from completed non-required courses
                completed_elective_credits_now = sum(
                    cc.course.credits for cc in CompletedCourse.objects.filter(
                        student=student
                    ).select_related('course')
                    if cc.course.id not in required_ids_now
                )

                # Credits from currently selected electives
                selected_credits_now = sum(
                    Course.objects.filter(id__in=current_elective_ids).values_list('credits', flat=True)
                )

                total_now = completed_elective_credits_now + selected_credits_now
                still_needed = max(0, elective_credits_required - total_now)

                auto_filled = []  # Track which courses were auto-added

                if still_needed > 0:
                    # Build exclusion set — don't pick anything already required,
                    # already completed, already selected, or Senior Project
                    exclude_from_pool = required_ids_now | current_elective_ids | completed_ids_now
                    if senior_project_id:
                        exclude_from_pool.add(senior_project_id)

                    # Get a random pool of courses to auto-fill from
                    available_pool = list(
                        Course.objects.exclude(id__in=exclude_from_pool).order_by('?')
                    )

                    # Add courses until we've filled the credit gap
                    credits_to_add = still_needed
                    for course in available_pool:
                        if credits_to_add <= 0:
                            break
                        StudentElective.objects.get_or_create(student=student, course=course)
                        auto_filled.append(course)
                        credits_to_add -= course.credits

                # ── Step 5: Save pinned course assignments ──────
                # Clear old pins, then save new ones from the drag-drop UI.
                # Each pinned item comes in as "course_id:Semester N"
                PinnedCourse.objects.filter(preference=preferences).delete()
                pinned_data = request.POST.getlist('pinned_courses')

                seen = set()  # Prevent the same course being pinned twice
                for item in pinned_data:
                    try:
                        course_id, semester_label = item.split(':')

                        # Skip if this course was already pinned in this save
                        if course_id in seen:
                            continue
                        seen.add(course_id)

                        course = Course.objects.get(id=course_id)

                        # Senior Project cannot be manually pinned —
                        # the recommender always places it in the last Fall
                        if senior_project_id and course.id == senior_project_id:
                            continue

                        # Validate that the course is offered in the correct season.
                        # Odd semester slots = Fall, Even semester slots = Spring.
                        slot_num = int(semester_label.replace('Semester ', ''))
                        slot_season = 'Fall' if slot_num % 2 == 1 else 'Spring'

                        # Block Fall-only courses from being pinned to Spring slots
                        if course.semester_offered == 'Fall' and slot_season == 'Spring':
                            continue
                        # Block Spring-only courses from being pinned to Fall slots
                        if course.semester_offered == 'Spring' and slot_season == 'Fall':
                            continue

                        PinnedCourse.objects.create(
                            preference=preferences,
                            course=course,
                            semester_label=semester_label
                        )
                    except (ValueError, Course.DoesNotExist):
                        pass  # Skip malformed entries silently

                # ── Step 6: Store notice in session & redirect ──
                # If electives were auto-filled, store a notice in the Django
                # session so it can be displayed on the schedule page.
                # Using session.pop() in the schedule view ensures it only
                # shows once and disappears on page refresh.
                #
                # IMPORTANT: We ALWAYS redirect to /schedule/ here.
                # The old code re-rendered the plan page when auto-fill happened,
                # which caused the Generate button to appear broken.
                if auto_filled:
                    auto_names = ', '.join(f"{c.course_code} ({c.course_name})" for c in auto_filled)
                    request.session['elective_notice'] = (
                        f"{len(auto_filled)} elective{'s were' if len(auto_filled) > 1 else ' was'} "
                        f"auto-selected to meet your {elective_credits_required}-credit requirement: "
                        f"{auto_names}. You can change these on the Plan page."
                    )

            except Exception as e:
                # Print the full error traceback to the terminal so we can debug it.
                # This catches any crash inside the save block and makes it visible
                # without swallowing the error silently.
                print("\n" + "=" * 60)
                print("ERROR IN PLAN SCHEDULE - save_preferences")
                print("=" * 60)
                traceback.print_exc()
                print("=" * 60 + "\n")
                raise  # Re-raise so Django also shows it in the browser error page

            # Always redirect to the schedule page after a successful save
            return redirect('schedule')

    # ── GET REQUEST — render the plan page ────────────────────
    context = {
        'majors': majors,
        'student': student,
        'preferences': preferences,
        'pinned_courses': pinned_courses,
        'all_remaining': all_remaining,       # Required courses not yet completed
        'all_electives': all_electives,       # Available elective options
        'selected_elective_ids': selected_elective_ids,  # IDs of already-selected electives
        'semester_slots': [f'Semester {i}' for i in range(1, 9)],  # 8 semester slots
        'elective_notice': elective_notice,   # Shown after auto-fill (usually None on GET)
        'elective_warning': elective_warning, # Shown when student needs more electives
    }
    return render(request, 'courses/plan_schedule.html', context)


# DOWNLOAD SCHEDULE PDF VIEW
def download_schedule_pdf(request, student_id):
    """
    Generates the student's graduation schedule as a downloadable PDF file.

    Uses the ReportLab library to build a formatted PDF document with:
    - A title header
    - A student info summary table (name, ID, major, GPA, graduation, etc.)
    - One section per semester showing course code, name, and credits
    - Color-coded table headers

    The PDF is built in memory using a BytesIO buffer and returned as
    an HTTP response with a Content-Disposition header that triggers
    the browser's download dialog.
    """
    student = get_object_or_404(Student, student_id=student_id)

    # Load preferences and pinned courses for the recommender
    preferences, _ = StudentPreference.objects.get_or_create(student=student)
    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    # Generate the full schedule using the same recommender as the schedule page
    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    # Build the PDF in memory — no temp files needed
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # ── PDF Styles ─────────────────────────────────────────────
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

    # ── Title ──────────────────────────────────────────────────
    title = Paragraph("DegreePath - Graduation Schedule", title_style)
    elements.append(title)

    # ── Student info summary table ─────────────────────────────
    grad_semester = date_to_semester(student.expected_graduation) or 'Not set'
    student_info = [
        ['Student:', f"{student.first_name} {student.last_name}"],
        ['Student ID:', student.student_id],
        ['Major:', student.major.name],
        ['Concentration:', student.get_concentration_display() if student.concentration else 'None'],
        ['GPA:', str(student.gpa) if student.gpa else 'Not set'],
        ['Expected Graduation:', grad_semester],
        ['Total Semesters:', str(full_plan['total_semesters'])],
    ]

    info_table = Table(student_info, colWidths=[2 * inch, 4 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),  # Gray label column
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),              # Bold labels
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ── One section per semester ───────────────────────────────
    for semester_plan in full_plan['schedule']:
        semester_heading = Paragraph(
            f"{semester_plan['semester']} — {semester_plan['total_credits']} credits",
            heading_style
        )
        elements.append(semester_heading)

        # Table with header row + one row per course
        course_data = [['Course Code', 'Course Name', 'Credits']]
        for course in semester_plan['courses']:
            course_data.append([
                course.course_code,
                course.course_name[:40],  # Truncate long names so they fit
                str(course.credits)
            ])

        course_table = Table(course_data, colWidths=[1.5 * inch, 4 * inch, 1 * inch])
        course_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),  # Blue header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),              # Beige rows
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        elements.append(course_table)
        elements.append(Spacer(1, 0.2 * inch))

    # Build the PDF and seek back to the start of the buffer
    doc.build(elements)
    buffer.seek(0)

    # Return as a downloadable file attachment
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DegreePath_Schedule_{student.student_id}.pdf"'
    return response