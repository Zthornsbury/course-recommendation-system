from courses.models import Course, CompletedCourse, Prerequisite, DegreeRequirement, Major, StudentElective
from typing import List, Dict, Set
from courses.course_config import COURSE_PREREQUISITES, CS_CORE_REQUIRED, CS_CONCENTRATION_AI, CS_CONCENTRATION_WEB, CS_CONCENTRATION_CYBER


class CourseRecommender:
    """
    Generates a semester-by-semester graduation schedule for a student based on:
    - Completed courses and prerequisite chains
    - Degree requirements for their major
    - Concentration track (AI / Web / Cybersecurity)
    - Student-selected electives
    - Credit limit per semester (default 18, reduced if GPA is low)
    - Course priority preference (BALANCED / GEN_ED_FIRST / CS_FIRST)
    - Senior Project (CSC4899) always placed in the last Fall semester
    """

    def __init__(self, student):
        self.student = student
        self.completed_courses = self._get_completed_courses()
        self.major = student.major

    # ── Get completed course IDs ────────────────────────────────
    def _get_completed_courses(self) -> Set[int]:
        """Return a set of course IDs the student has already completed"""
        return set(
            CompletedCourse.objects.filter(student=self.student).values_list('course_id', flat=True)
        )

    # ── Get prerequisite IDs for a course ──────────────────────
    def _get_prerequisites(self, course: Course) -> Set[int]:
        """
        Return prerequisite course IDs for a given course.
        Checks the database first, falls back to course_config if empty.
        """
        from courses.course_config import COURSE_PREREQUISITES

        # Try database prerequisites first
        db_prereqs = set(
            Prerequisite.objects.filter(course=course).values_list('prerequisite_course_id', flat=True)
        )

        if db_prereqs:
            return db_prereqs

        # Fall back to course_config if no DB prerequisites recorded
        config_prereq_codes = COURSE_PREREQUISITES.get(course.course_code, [])
        if config_prereq_codes:
            return set(
                Course.objects.filter(course_code__in=config_prereq_codes).values_list('id', flat=True)
            )

        return set()

    # ── Check if student has met prerequisites ──────────────────
    def _has_prerequisites(self, course: Course) -> bool:
        """Check if the student has completed all prerequisites for a course"""
        required_prerequisites = self._get_prerequisites(course)
        return required_prerequisites.issubset(self.completed_courses)

    # ── Get all required courses for the major ──────────────────
    def _get_required_courses_for_major(self) -> List[Course]:
        """Return all courses marked REQUIRED for the student's major"""
        if not self.major:
            return []

        return list(
            Course.objects
            .filter(
                degreerequirement__major=self.major,
                degreerequirement__requirement_type='REQUIRED'
            )
            .distinct()
        )

    # ── Get remaining required courses ─────────────────────────
    def _get_remaining_courses(self) -> List[Course]:
        """Return required courses the student still needs to take"""
        required_courses = self._get_required_courses_for_major()
        return [c for c in required_courses if c.id not in self.completed_courses]

    # ── Check prerequisites against a custom completed set ──────
    def _has_prerequisites_from_set(self, course: Course, completed_set: Set[int]) -> bool:
        """
        Check if prerequisites are met using a given completed set.
        Used inside the scheduling loop where completed grows each semester.
        """
        prerequisites = self._get_prerequisites(course)
        return prerequisites.issubset(completed_set)

    # ── Main scheduling method ──────────────────────────────────
    def get_full_schedule(self, max_credits_per_semester=18, pinned_courses=None, priority='BALANCED'):
        """
        Generate a complete semester-by-semester schedule until graduation.

        Parameters:
        - max_credits_per_semester: credit cap per semester (reduced automatically if GPA is low)
        - pinned_courses: dict of {semester_label: [course_id, ...]} for user-pinned courses
        - priority: BALANCED / GEN_ED_FIRST / CS_FIRST — controls course ordering each semester

        Senior Project (CSC4899) is always placed in the last Fall semester.
        """
        schedule = []
        completed = self.completed_courses.copy()  # Working copy grows as courses are scheduled
        current_semester = 'Fall'
        semester_count = 0
        max_semesters = 10
        year = 2026

        pinned_courses = pinned_courses or {}

        # ── Auto-reduce credits if GPA is low ──────────────────
        # Students struggling academically should take lighter loads
        if self.student.gpa:
            gpa = float(self.student.gpa)
            if gpa < 2.5:
                # GPA below 2.5 — cap at 9 credits to help student recover
                max_credits_per_semester = min(max_credits_per_semester, 9)
            elif gpa < 3.0:
                # GPA below 3.0 — cap at 12 credits
                max_credits_per_semester = min(max_credits_per_semester, 12)

        # ── Build the required course pool ─────────────────────
        # Start with all courses marked REQUIRED in DegreeRequirement
        all_required = set(
            DegreeRequirement.objects
            .filter(major=self.major)
            .values_list('course_id', flat=True)
        )

        # ── Pull Senior Project out of normal pool ──────────────
        # CSC4899 is handled separately — always placed in last Fall semester
        senior_project = Course.objects.filter(course_code='CSC4899').first()
        senior_project_id = senior_project.id if senior_project else None
        reserve_senior_project = False

        if senior_project_id and senior_project_id in all_required:
            all_required.discard(senior_project_id)
            reserve_senior_project = True

        # Don't reserve Senior Project if student already completed it
        if senior_project_id and senior_project_id in completed:
            reserve_senior_project = False

        # ── Add concentration courses ───────────────────────────
        # Students with a concentration get additional required courses
        if self.student.concentration:
            concentration_map = {
                'AI': CS_CONCENTRATION_AI,
                'WEB': CS_CONCENTRATION_WEB,
                'CYBER': CS_CONCENTRATION_CYBER,
            }
            concentration_codes = concentration_map.get(self.student.concentration, [])
            if concentration_codes:
                concentration_ids = set(
                    Course.objects.filter(
                        course_code__in=concentration_codes
                    ).values_list('id', flat=True)
                )
                all_required = all_required | concentration_ids

        # ── Add student-selected electives ─────────────────────
        # Electives chosen on the Plan page get treated as required courses
        elective_ids = set(
            StudentElective.objects.filter(student=self.student).values_list('course_id', flat=True)
        )
        all_required = all_required | elective_ids

        # ── Final safety: ensure Senior Project not re-added ────
        # Concentration or elective additions could re-introduce it
        if senior_project_id:
            all_required.discard(senior_project_id)

        # ── Main scheduling loop ────────────────────────────────
        while semester_count < max_semesters:
            semester_count += 1

            # Stop once all required courses (except Senior Project) are scheduled
            if completed >= all_required:
                break

            semester_label = f'Semester {semester_count}'
            semester_courses = []
            total_credits = 0

            # Step 1: Add pinned courses for this semester slot first
            # Pinned courses are placed before auto-fill so student preferences are respected
            pinned_for_this_slot = pinned_courses.get(semester_label, [])
            for course_id in pinned_for_this_slot:
                try:
                    # Skip Senior Project even if somehow pinned
                    if senior_project_id and int(course_id) == senior_project_id:
                        continue
                    course = Course.objects.get(id=course_id)
                    if course.id not in completed and self._has_prerequisites_from_set(course, completed):
                        semester_courses.append(course)
                        total_credits += course.credits
                except Course.DoesNotExist:
                    pass

            # Track pinned course IDs so we don't add them again below
            pinned_ids_this_slot = {c.id for c in semester_courses}

            # Step 2: Fill remaining credit space with available courses
            # Only include courses offered in the current semester (Fall/Spring/Both)
            available_courses = list(Course.objects.filter(
                id__in=all_required - completed,
                semester_offered__in=[current_semester, 'Both']
            ).exclude(id__in=pinned_ids_this_slot))

            # Sort courses based on student's priority preference
            if priority == 'GEN_ED_FIRST':
                # Non-CS courses come first — good for knocking out gen ed early
                available_courses.sort(
                    key=lambda c: 0 if c.department != 'Computer Science' else 1
                )
            elif priority == 'CS_FIRST':
                # CS courses come first — good for building technical skills early
                available_courses.sort(
                    key=lambda c: 0 if c.department == 'Computer Science' else 1
                )
            # BALANCED — no sorting, natural DB order

            # Add courses until the credit limit is reached
            for course in available_courses:
                if self._has_prerequisites_from_set(course, completed):
                    if total_credits + course.credits <= max_credits_per_semester:
                        semester_courses.append(course)
                        total_credits += course.credits

            # Mark all scheduled courses as completed so next semester's prereq check works
            for course in semester_courses:
                completed.add(course.id)

            # Only add the semester to the schedule if it has at least one course
            if semester_courses:
                schedule.append({
                    'semester': f"{current_semester} {year}",
                    'courses': semester_courses,
                    'total_credits': total_credits
                })

            # Alternate between Fall and Spring, incrementing year after each Spring
            if current_semester == 'Fall':
                current_semester = 'Spring'
            else:
                current_semester = 'Fall'
                year += 1

        # ── Place Senior Project in last Fall semester ──────────
        # After all other courses are scheduled, find the last Fall semester
        # and append Senior Project there. This ensures it's in the student's
        # final Fall semester as required by the FSC CS degree program.
        if reserve_senior_project:
            placed = False

            # Search backwards through the schedule for the last Fall semester
            for sem in reversed(schedule):
                if 'Fall' in sem['semester']:
                    sem['courses'].append(senior_project)
                    sem['total_credits'] += senior_project.credits
                    completed.add(senior_project_id)
                    placed = True
                    break

            # If no Fall semester exists in the schedule, create one
            if not placed:
                if schedule:
                    last_sem = schedule[-1]['semester']
                    last_year = int(last_sem.split()[-1])
                    last_season = last_sem.split()[0]
                    # If last semester was Spring, use that same year's Fall
                    # If last semester was Fall, use the next year's Fall
                    fall_year = last_year if last_season == 'Spring' else last_year + 1
                else:
                    fall_year = year

                schedule.append({
                    'semester': f"Fall {fall_year}",
                    'courses': [senior_project],
                    'total_credits': senior_project.credits
                })
                completed.add(senior_project_id)

        return {
            'schedule': schedule,
            'total_semesters': len(schedule),
            'courses_remaining': len(all_required - completed)
        }

    # ── Get detailed course info ────────────────────────────────
    def get_course_details(self, course: Course) -> Dict:
        """Return detailed info about a course including its prerequisites"""
        prerequisites = self._get_prerequisites(course)
        prerequisite_courses = Course.objects.filter(id__in=prerequisites)

        return {
            'course': course,
            'prerequisites': list(prerequisite_courses),
            'prerequisites_met': self._has_prerequisites(course),
        }