from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from courses.recommender import CourseRecommender
import datetime
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
from courses.models import Student, Course, CompletedCourse, Prerequisite, DegreeRequirement, Major, StudentPreference, PinnedCourse, StudentElective
from django.contrib.auth.models import User
from courses.course_config import COURSE_PREREQUISITES, CS_CORE_REQUIRED, CS_CONCENTRATION_AI, CS_CONCENTRATION_WEB, CS_CONCENTRATION_CYBER


# ── Helper: convert "Spring-2028" or "Fall-2028" to a date object ──────────
def semester_to_date(semester_str):
    """Convert semester string like 'Spring-2028' to a datetime.date object"""
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


# ── Helper: convert a date object to a semester string ─────────────────────
def date_to_semester(date_obj):
    """Convert a date object to a readable semester like 'Spring 2028'"""
    if not date_obj:
        return None
    if date_obj.month <= 7:
        return f"Spring {date_obj.year}"
    else:
        return f"Fall {date_obj.year}"


# ── Helper: get elective requirement for a student ─────────────────────────
def get_elective_requirement(student):
    """
    Return the number of elective credits required based on concentration.
    - With concentration: 8 credits of electives required
    - Without concentration: 20 credits of electives required
    """
    return 8 if student.concentration else 20


# ============================================================
# LOGIN VIEW
# ============================================================
def login_view(request):
    """Show login form and authenticate the user"""

    # If already logged in, skip login and go straight to dashboard
    if request.user.is_authenticated:
        try:
            return redirect('dashboard', student_id=request.user.student.student_id)
        except:
            pass

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                return redirect('dashboard', student_id=user.student.student_id)
            except:
                logout(request)
                return render(request, 'courses/login.html', {
                    'error': 'No student profile found for this account. Please register a new account.'
                })

    return render(request, 'courses/login.html')


# ============================================================
# LOGOUT VIEW
# ============================================================
def logout_view(request):
    """Log the user out and redirect to login page"""
    logout(request)
    return redirect('login')


# ============================================================
# REGISTER VIEW
# ============================================================
def register_view(request):
    """Handle new student account creation with password complexity validation"""

    current_year = datetime.date.today().year
    graduation_years = range(current_year, current_year + 8)

    if request.method == 'POST':
        username = request.POST.get('username')

        # Student ID must be numeric only
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

        if password != confirm_password:
            return render(request, 'courses/register.html', {
                'error': 'Passwords do not match.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        # Password complexity checks
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

        if User.objects.filter(username=username).exists():
            return render(request, 'courses/register.html', {
                'error': 'Username already exists.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        if Student.objects.filter(student_id=username).exists():
            return render(request, 'courses/register.html', {
                'error': 'A student with that ID already exists.',
                'majors': Major.objects.all(),
                'graduation_years': graduation_years,
            })

        user = User.objects.create_user(username=username, password=password)
        major = Major.objects.get(id=major_id) if major_id else None
        graduation_date = semester_to_date(graduation_semester)

        student = Student.objects.create(
            user=user,
            student_id=username,
            first_name=first_name,
            last_name=last_name,
            major=major,
            concentration=concentration,
            expected_graduation=graduation_date,
            gpa=gpa if gpa else None,
        )

        login(request, user)
        return redirect('dashboard', student_id=student.student_id)

    majors = Major.objects.all()
    return render(request, 'courses/register.html', {
        'majors': majors,
        'graduation_years': graduation_years,
    })


# ============================================================
# INDEX / HOME VIEW
# ============================================================
@login_required(login_url='/login/')
def index(request):
    """Home page — student lookup or creation"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        major_id = request.POST.get('major')
        graduation_date = request.POST.get('graduation_date')
        gpa = request.POST.get('gpa')

        major = Major.objects.get(id=major_id) if major_id else None

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


# ============================================================
# STUDENT DASHBOARD VIEW
# ============================================================
@login_required(login_url='/login/')
def student_dashboard(request, student_id):
    """Main student dashboard — stats, progress bar, completed courses, warnings"""
    student = get_object_or_404(Student, student_id=student_id)

    current_year = datetime.date.today().year
    graduation_years = range(current_year, current_year + 8)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Update student profile ─────────────────────────────────
        if action == 'update_student':
            gpa = request.POST.get('gpa')
            graduation_semester = request.POST.get('graduation_semester', '')
            concentration = request.POST.get('concentration', '')

            if gpa:
                student.gpa = gpa

            graduation_date = semester_to_date(graduation_semester)
            if graduation_date:
                student.expected_graduation = graduation_date

            student.concentration = concentration
            student.save()
            return redirect('dashboard', student_id=student_id)

        # ── Add a completed course ─────────────────────────────────
        else:
            course_id = request.POST.get('course_id')
            grade = request.POST.get('grade')

            course = Course.objects.get(id=course_id)

            completed_ids = set(
                CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
            )

            required_prereqs = set(
                Prerequisite.objects.filter(course=course).values_list('prerequisite_course_id', flat=True)
            )

            if not required_prereqs:
                config_codes = COURSE_PREREQUISITES.get(course.course_code, [])
                if config_codes:
                    required_prereqs = set(
                        Course.objects.filter(course_code__in=config_codes).values_list('id', flat=True)
                    )

            if not required_prereqs.issubset(completed_ids):
                missing = Course.objects.filter(
                    id__in=required_prereqs - completed_ids
                ).values_list('course_code', flat=True)

                completed_courses = CompletedCourse.objects.filter(student=student).select_related('course')
                completed_ids_set = set(
                    CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
                )
                all_courses = Course.objects.exclude(id__in=completed_ids_set).order_by('course_code')
                preferences, _ = StudentPreference.objects.get_or_create(student=student)
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

                gpa_warning = None
                if student.gpa:
                    gpa = float(student.gpa)
                    if gpa < 2.0:
                        gpa_warning = 'probation'
                    elif gpa < 3.0:
                        gpa_warning = 'at_risk'

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

            CompletedCourse.objects.create(
                student=student,
                course=course,
                grade=grade,
                completion_date=datetime.date.today()
            )
            return redirect('dashboard', student_id=student_id)

    # ── GET REQUEST ────────────────────────────────────────────

    completed_courses = CompletedCourse.objects.filter(student=student).select_related('course')
    completed_ids = set(
        CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
    )
    all_courses = Course.objects.exclude(id__in=completed_ids).order_by('course_code')

    preferences, _ = StudentPreference.objects.get_or_create(student=student)
    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    # Graduation warning logic
    is_behind = False
    realistic_graduation = None
    realistic_graduation_semester = None
    expected_graduation_semester = date_to_semester(student.expected_graduation)

    if student.expected_graduation:
        remaining_credits = sum(
            semester['total_credits'] for semester in full_plan['schedule']
        )
        credits_per_semester = 18
        semesters_needed = -(-remaining_credits // credits_per_semester)
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

        is_behind = realistic_graduation > expected

    credits_completed = sum(cc.course.credits for cc in completed_courses)
    total_credits_required = student.major.total_credits_required if student.major else 124
    progress_percent = min(int((credits_completed / total_credits_required) * 100), 100)

    gpa_warning = None
    if student.gpa:
        gpa = float(student.gpa)
        if gpa < 2.0:
            gpa_warning = 'probation'
        elif gpa < 3.0:
            gpa_warning = 'at_risk'

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
# ============================================================
@login_required(login_url='/login/')
def delete_completed_course(request, student_id, course_id):
    """Remove a completed course from the student's record"""
    student = get_object_or_404(Student, student_id=student_id)

    try:
        if request.user.student != student:
            return redirect('dashboard', student_id=student_id)
    except:
        return redirect('dashboard', student_id=student_id)

    CompletedCourse.objects.filter(student=student, course_id=course_id).delete()
    return redirect('dashboard', student_id=student_id)


# ============================================================
# SCHEDULE VIEW
# ============================================================
@login_required(login_url='/login/')
def schedule(request):
    """Show the generated graduation schedule using saved preferences"""
    try:
        student = request.user.student
    except:
        return redirect('login')

    preferences, _ = StudentPreference.objects.get_or_create(student=student)

    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    context = {
        'student': student,
        'schedule': full_plan['schedule'],
        'total_semesters': full_plan['total_semesters'],
        'courses_remaining': full_plan['courses_remaining'],
        'target_credits': preferences.target_credits_per_semester,
    }
    return render(request, 'courses/schedule.html', context)


# ============================================================
# GET STUDENT API ENDPOINT
# ============================================================
def get_student(request):
    """API endpoint to look up a student by ID"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id)
            return redirect('dashboard', student_id=student_id)
        except Student.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)

    return JsonResponse({'error': 'Invalid request'}, status=400)


# ============================================================
# COURSE CATALOG VIEW
# ============================================================
@login_required(login_url='/login/')
def course_catalog(request):
    """Display all courses split into CS Major and general education sections"""

    cs_courses = Course.objects.filter(department='Computer Science').order_by('course_code')
    cs_codes = set(cs_courses.values_list('course_code', flat=True))
    cs_names = set(name.lower().strip() for name in cs_courses.values_list('course_name', flat=True))

    other_courses = Course.objects.exclude(department='Computer Science').order_by('department', 'course_code')
    other_courses = [
        c for c in other_courses
        if c.course_code not in cs_codes and c.course_name.lower().strip() not in cs_names
    ]

    return render(request, 'courses/catalog.html', {
        'cs_courses': cs_courses,
        'other_courses': other_courses,
    })


# ============================================================
# PREREQUISITES VIEW
# ============================================================
@login_required(login_url='/login/')
def prerequisites(request):
    """Display prerequisite relationships for all courses"""
    all_courses = Course.objects.all().order_by('course_code')
    prereq_map = {}

    for course in all_courses:
        db_prereqs = Prerequisite.objects.filter(course=course).select_related('prerequisite_course')

        if db_prereqs.exists():
            prereq_map[course.course_code] = {
                'course': course,
                'prerequisites': [p.prerequisite_course for p in db_prereqs]
            }
        else:
            config_codes = COURSE_PREREQUISITES.get(course.course_code, [])
            if config_codes:
                config_prereq_courses = Course.objects.filter(course_code__in=config_codes)
                prereq_map[course.course_code] = {
                    'course': course,
                    'prerequisites': list(config_prereq_courses)
                }

    return render(request, 'courses/prerequisites.html', {'prereq_map': prereq_map})


# ============================================================
# PLAN SCHEDULE VIEW
# ============================================================
@login_required(login_url='/login/')
def plan_schedule(request):
    """Plan My Schedule — elective selection, drag-drop pinning, credit preferences"""
    majors = Major.objects.all()

    try:
        student = request.user.student
        student_id = student.student_id
    except:
        student = None
        student_id = None

    preferences = None
    pinned_courses = []
    all_remaining = []
    all_electives = []
    selected_elective_ids = set()
    senior_project_id = None
    elective_notice = None      # Message shown when electives are auto-filled
    elective_warning = None     # Warning shown when student hasn't selected enough

    if student:
        preferences, _ = StudentPreference.objects.get_or_create(student=student)
        pinned_courses = PinnedCourse.objects.filter(preference=preferences).select_related('course')

        completed_ids = set(
            CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
        )

        # Build required course pool
        required_ids = set(
            DegreeRequirement.objects.filter(major=student.major).values_list('course_id', flat=True)
        )

        # Add concentration courses
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

        # Get student's currently selected electives
        selected_elective_ids = set(
            StudentElective.objects.filter(student=student).values_list('course_id', flat=True)
        )
        required_ids = required_ids | selected_elective_ids

        # Exclude Senior Project from pool
        senior_project = Course.objects.filter(course_code='CSC4899').first()
        senior_project_id = senior_project.id if senior_project else None
        exclude_ids = {senior_project_id} if senior_project_id else set()

        all_remaining = Course.objects.filter(
            id__in=required_ids - completed_ids
        ).exclude(id__in=exclude_ids).order_by('course_code')

        # All available electives (not already required or completed)
        all_electives = Course.objects.exclude(
            id__in=required_ids
        ).exclude(
            id__in=completed_ids
        ).order_by('department', 'course_code')

        # ── Calculate elective requirement ─────────────────────
        elective_credits_required = get_elective_requirement(student)

        # Count credits from already-completed electives
        # (courses that are completed but not part of degree requirements or concentration)
        completed_elective_credits = sum(
            cc.course.credits for cc in CompletedCourse.objects.filter(
                student=student
            ).select_related('course')
            if cc.course.id not in required_ids
        )

        # Count credits from currently selected electives
        selected_elective_credits = sum(
            Course.objects.filter(id__in=selected_elective_ids).values_list('credits', flat=True)
        )

        total_elective_credits = completed_elective_credits + selected_elective_credits
        elective_credits_still_needed = max(0, elective_credits_required - total_elective_credits)

        # Show warning on the page about elective requirement
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
            # Save credit target
            target_credits = request.POST.get('target_credits')
            if target_credits:
                preferences.target_credits_per_semester = max(9, int(target_credits))

            # Save priority
            priority = request.POST.get('priority', 'BALANCED')
            preferences.priority = priority
            preferences.save()

            # ── Save selected electives ────────────────────────────
            StudentElective.objects.filter(student=student).delete()
            selected_electives = request.POST.getlist('selected_electives')

            # Add all manually selected electives
            for course_id in selected_electives:
                try:
                    course = Course.objects.get(id=course_id)
                    StudentElective.objects.get_or_create(student=student, course=course)
                except Course.DoesNotExist:
                    pass

            # ── Auto-fill electives if not enough selected ─────────
            # Recalculate after saving manual selections
            elective_credits_required = get_elective_requirement(student)

            completed_ids_now = set(
                CompletedCourse.objects.filter(student=student).values_list('course_id', flat=True)
            )
            required_ids_now = set(
                DegreeRequirement.objects.filter(major=student.major).values_list('course_id', flat=True)
            )
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

            # Credits from selected electives
            selected_credits_now = sum(
                Course.objects.filter(id__in=current_elective_ids).values_list('credits', flat=True)
            )

            total_now = completed_elective_credits_now + selected_credits_now
            still_needed = max(0, elective_credits_required - total_now)

            auto_filled = []

            if still_needed > 0:
                # Build pool of available electives to auto-fill from
                # Exclude: degree requirements, concentration courses, already selected, already completed
                exclude_from_pool = required_ids_now | current_elective_ids | completed_ids_now
                if senior_project_id:
                    exclude_from_pool.add(senior_project_id)

                available_pool = list(
                    Course.objects.exclude(id__in=exclude_from_pool).order_by('?')  # Random order
                )

                # Pick courses until we meet the credit requirement
                credits_to_add = still_needed
                for course in available_pool:
                    if credits_to_add <= 0:
                        break
                    StudentElective.objects.get_or_create(student=student, course=course)
                    auto_filled.append(course)
                    credits_to_add -= course.credits

            # Build elective notice to show after save
            if auto_filled:
                auto_names = ', '.join(f"{c.course_code} ({c.course_name})" for c in auto_filled)
                elective_notice = f"{len(auto_filled)} elective{'s were' if len(auto_filled) > 1 else ' was'} auto-selected to meet your {elective_credits_required}-credit requirement: {auto_names}. You can change these below."

            # ── Save pinned courses ────────────────────────────────
            PinnedCourse.objects.filter(preference=preferences).delete()
            pinned_data = request.POST.getlist('pinned_courses')

            seen = set()
            for item in pinned_data:
                try:
                    course_id, semester_label = item.split(':')

                    if course_id in seen:
                        continue
                    seen.add(course_id)

                    course = Course.objects.get(id=course_id)

                    # Never allow Senior Project to be manually pinned
                    if senior_project_id and course.id == senior_project_id:
                        continue

                    # Validate semester compatibility
                    slot_num = int(semester_label.replace('Semester ', ''))
                    slot_season = 'Fall' if slot_num % 2 == 1 else 'Spring'

                    if course.semester_offered == 'Fall' and slot_season == 'Spring':
                        continue
                    if course.semester_offered == 'Spring' and slot_season == 'Fall':
                        continue

                    PinnedCourse.objects.create(
                        preference=preferences,
                        course=course,
                        semester_label=semester_label
                    )
                except (ValueError, Course.DoesNotExist):
                    pass

            # If electives were auto-filled, stay on plan page to show the notice
            # Otherwise go straight to schedule
            if auto_filled or elective_notice:
                # Rebuild context to re-render plan page with notice
                selected_elective_ids = set(
                    StudentElective.objects.filter(student=student).values_list('course_id', flat=True)
                )
                required_ids_final = required_ids_now | selected_elective_ids
                all_remaining = Course.objects.filter(
                    id__in=required_ids_final - completed_ids_now
                ).exclude(id__in=exclude_ids).order_by('course_code')
                all_electives = Course.objects.exclude(
                    id__in=required_ids_final
                ).exclude(
                    id__in=completed_ids_now
                ).order_by('department', 'course_code')
                pinned_courses = PinnedCourse.objects.filter(preference=preferences).select_related('course')

                context = {
                    'majors': majors,
                    'student': student,
                    'preferences': preferences,
                    'pinned_courses': pinned_courses,
                    'all_remaining': all_remaining,
                    'all_electives': all_electives,
                    'selected_elective_ids': selected_elective_ids,
                    'semester_slots': [f'Semester {i}' for i in range(1, 9)],
                    'elective_notice': elective_notice,
                    'elective_warning': None,  # Clear warning since we just auto-filled
                }
                return render(request, 'courses/plan_schedule.html', context)

            return redirect('schedule')

    context = {
        'majors': majors,
        'student': student,
        'preferences': preferences,
        'pinned_courses': pinned_courses,
        'all_remaining': all_remaining,
        'all_electives': all_electives,
        'selected_elective_ids': selected_elective_ids,
        'semester_slots': [f'Semester {i}' for i in range(1, 9)],
        'elective_notice': elective_notice,
        'elective_warning': elective_warning,
    }
    return render(request, 'courses/plan_schedule.html', context)


# ============================================================
# DOWNLOAD SCHEDULE PDF VIEW
# ============================================================
def download_schedule_pdf(request, student_id):
    """Generate and download the student's graduation schedule as a PDF"""
    student = get_object_or_404(Student, student_id=student_id)

    preferences, _ = StudentPreference.objects.get_or_create(student=student)
    pinned_dict = {}
    for pinned in PinnedCourse.objects.filter(preference=preferences):
        pinned_dict.setdefault(pinned.semester_label, []).append(pinned.course.id)

    recommender = CourseRecommender(student)
    full_plan = recommender.get_full_schedule(
        max_credits_per_semester=preferences.target_credits_per_semester,
        pinned_courses=pinned_dict,
        priority=preferences.priority
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

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

    title = Paragraph("DegreePath - Graduation Schedule", title_style)
    elements.append(title)

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

    for semester_plan in full_plan['schedule']:
        semester_heading = Paragraph(
            f"{semester_plan['semester']} — {semester_plan['total_credits']} credits",
            heading_style
        )
        elements.append(semester_heading)

        course_data = [['Course Code', 'Course Name', 'Credits']]
        for course in semester_plan['courses']:
            course_data.append([
                course.course_code,
                course.course_name[:40],
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

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DegreePath_Schedule_{student.student_id}.pdf"'
    return response