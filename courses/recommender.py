import random
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
    - Minimum 9 credits per semester enforced — electives are auto-filled if short
    - Credit cap respected EVERYWHERE including Senior Project placement
    - Priority preference respected in BOTH required course ordering AND
      elective auto-fill padding (fixes CS First not working correctly)
    """

    MIN_CREDITS_PER_SEMESTER = 9

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

    # ── Elective padding helper ─────────────────────────────────
    def _pad_semester_with_electives(self, sem: dict, exclude_ids: Set[int],
                                      max_credits: int, completed_set: Set[int],
                                      priority: str = 'BALANCED') -> None:
        """
        Auto-fill a semester with electives until it reaches MIN_CREDITS_PER_SEMESTER.

        Now accepts a priority parameter so the order in which electives are
        considered matches the student's preference:
        - CS_FIRST:     CS department courses are tried first
        - GEN_ED_FIRST: Non-CS courses are tried first
        - BALANCED:     Random order (varied each generation)

        This fixes the bug where CS First priority was being applied to required
        courses but ignored during elective padding, causing gen-ed electives to
        appear before CS courses when semesters needed to be padded.

        Each elective candidate must also pass FOUR checks before being added:
        1. Prerequisites met
        2. No department conflict (no two courses from same dept in same semester)
        3. Fits within the credit cap
        4. Not already in the exclude set
        """
        season = 'Fall' if 'Fall' in sem['semester'] else 'Spring'

        # Build a set of departments already in this semester
        # to prevent duplicate-department pairings like BIO1005 + BIO1050
        departments_in_semester = {c.department for c in sem['courses']}

        # Fetch all candidate electives for this season
        padding_pool = list(
            Course.objects.exclude(
                id__in=exclude_ids
            ).filter(
                semester_offered__in=[season, 'Both']
            )
        )

        # ── Sort padding pool by priority ───────────────────────
        # This is the fix — the padding pool is now sorted the same way
        # the main required courses list is sorted, so the student's
        # priority preference applies to auto-filled electives too.
        #
        # CS_FIRST:     CS department courses bubble to the top
        # GEN_ED_FIRST: Non-CS courses bubble to the top
        # BALANCED:     Shuffle randomly so it varies each time
        if priority == 'CS_FIRST':
            padding_pool.sort(
                key=lambda c: 0 if c.department == 'Computer Science' else 1
            )
        elif priority == 'GEN_ED_FIRST':
            padding_pool.sort(
                key=lambda c: 0 if c.department != 'Computer Science' else 1
            )
        else:
            # BALANCED — random order gives variety instead of always
            # picking the same courses in DB insertion order
            random.shuffle(padding_pool)

        for elective in padding_pool:
            # Stop once we've hit the minimum credit threshold
            if sem['total_credits'] >= self.MIN_CREDITS_PER_SEMESTER:
                break

            # ── Check 1: Prerequisites ──────────────────────────
            # Don't schedule a course the student hasn't unlocked yet.
            # Uses the live completed_set so checks reflect the current
            # state of the schedule, not just the initial completed courses.
            if not self._has_prerequisites_from_set(elective, completed_set):
                continue

            # ── Check 2: Department conflict ────────────────────
            # Don't add a second course from the same department in the
            # same semester. Prevents redundant pairings like:
            # BIO1005 (Topics in Biology) + BIO1050 (Biology I) together,
            # or ART1110 + ART1120 both in the same term.
            if elective.department in departments_in_semester:
                continue

            # ── Check 3: Credit cap ─────────────────────────────
            # Strictly enforce the student's credit preference.
            # This ensures a 12-credit preference never produces a
            # 16-credit semester through padding.
            if sem['total_credits'] + elective.credits > max_credits:
                continue

            # All checks passed — add the elective to the semester
            sem['courses'].append(elective)
            sem['total_credits'] += elective.credits
            departments_in_semester.add(elective.department)

            # Save to StudentElective so the Plan page stays in sync
            # and this elective isn't re-scheduled in a future semester
            StudentElective.objects.get_or_create(
                student=self.student,
                course=elective
            )

    # ── Main scheduling method ──────────────────────────────────
    def get_full_schedule(self, max_credits_per_semester=18, pinned_courses=None, priority='BALANCED'):
        """
        Generate a complete semester-by-semester schedule until graduation.

        Parameters:
        - max_credits_per_semester: credit cap per semester (reduced automatically if GPA is low)
        - pinned_courses: dict of {semester_label: [course_id, ...]} for user-pinned courses
        - priority: BALANCED / GEN_ED_FIRST / CS_FIRST — controls course ordering each semester
                    NOW APPLIED TO BOTH required courses AND elective auto-fill padding

        Key rules:
        - Senior Project (CSC4899) always placed in the last Fall semester
        - Every semester must have at least 9 credits (MIN_CREDITS_PER_SEMESTER)
        - If short, electives are auto-filled respecting priority, prereqs, dept conflicts, and cap
        - Credit cap is respected everywhere — including Senior Project placement
        - The final semester is always published regardless of credit count
        """
        schedule = []
        completed = self.completed_courses.copy()  # Working copy grows as courses are scheduled
        current_semester = 'Fall'
        semester_count = 0
        max_semesters = 16
        year = 2026

        pinned_courses = pinned_courses or {}

        # ── Auto-reduce credits if GPA is low ──────────────────
        # Students struggling academically should take lighter loads.
        # Stacks on the student's preference — if preference is 12
        # and GPA < 2.5, effective cap becomes min(12, 9) = 9
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
        # CSC4899 is handled separately — always placed in last Fall semester.
        # Removed from all_required so the main loop doesn't schedule it early.
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
        # Electives chosen on the Plan page are treated like required courses
        # so they get scheduled alongside core requirements
        elective_ids = set(
            StudentElective.objects.filter(student=self.student).values_list('course_id', flat=True)
        )
        all_required = all_required | elective_ids

        # ── Final safety: ensure Senior Project not re-added ────
        # Concentration or elective additions could accidentally re-introduce it
        if senior_project_id:
            all_required.discard(senior_project_id)

        # ── Stuck detection setup ───────────────────────────────
        # If the completed set doesn't grow between iterations, all remaining
        # courses are locked behind prerequisites — break to avoid infinite loop
        previous_completed_size = -1

        # ── Main scheduling loop ────────────────────────────────
        while semester_count < max_semesters:
            semester_count += 1

            # Stop once all required courses (except Senior Project) are scheduled
            if completed >= all_required:
                break

            # Stuck detection — nothing was schedulable last iteration
            if len(completed) == previous_completed_size:
                break
            previous_completed_size = len(completed)

            semester_label = f'Semester {semester_count}'
            semester_courses = []
            total_credits = 0

            # ── Step 1: Add pinned courses first ────────────────
            # Pinned courses from the drag-and-drop UI are placed before
            # auto-fill so student's manual preferences are always respected
            pinned_for_this_slot = pinned_courses.get(semester_label, [])
            for course_id in pinned_for_this_slot:
                try:
                    # Never pin Senior Project — it's always placed by dedicated logic
                    if senior_project_id and int(course_id) == senior_project_id:
                        continue
                    course = Course.objects.get(id=course_id)
                    if course.id not in completed and self._has_prerequisites_from_set(course, completed):
                        # Respect the credit cap even for pinned courses
                        if total_credits + course.credits <= max_credits_per_semester:
                            semester_courses.append(course)
                            total_credits += course.credits
                except Course.DoesNotExist:
                    pass

            # Track pinned IDs so we don't double-add them below
            pinned_ids_this_slot = {c.id for c in semester_courses}

            # ── Step 2: Fill with available required courses ─────
            # Only include courses offered in the current season (Fall/Spring/Both)
            available_courses = list(Course.objects.filter(
                id__in=all_required - completed,
                semester_offered__in=[current_semester, 'Both']
            ).exclude(id__in=pinned_ids_this_slot))

            # ── Sort by priority preference ─────────────────────
            # CS_FIRST:     CS courses come first each semester
            # GEN_ED_FIRST: Non-CS courses come first each semester
            # BALANCED:     Natural DB order (no sorting)
            if priority == 'GEN_ED_FIRST':
                available_courses.sort(
                    key=lambda c: 0 if c.department != 'Computer Science' else 1
                )
            elif priority == 'CS_FIRST':
                available_courses.sort(
                    key=lambda c: 0 if c.department == 'Computer Science' else 1
                )

            # Add required courses until the credit cap is reached
            for course in available_courses:
                if self._has_prerequisites_from_set(course, completed):
                    if total_credits + course.credits <= max_credits_per_semester:
                        semester_courses.append(course)
                        total_credits += course.credits

            # ── Step 3: Auto-fill if below minimum credits ───────
            # If this semester has fewer than 9 credits, pad it with electives.
            # The last semester is always published as-is so students at
            # the end of their degree don't get stuck in an infinite loop.
            remaining_after = all_required - completed - {c.id for c in semester_courses}
            # Don't treat this as the last semester if Senior Project still needs placing
            is_last_semester = len(remaining_after) == 0 and not reserve_senior_project

            if total_credits < self.MIN_CREDITS_PER_SEMESTER and not is_last_semester:
                # Build exclusion set — don't re-add anything already scheduled
                already_in_semester = {c.id for c in semester_courses}
                exclude_from_padding = (
                    all_required          # don't double-add required courses
                    | completed           # don't re-add completed courses
                    | already_in_semester # don't duplicate this semester's courses
                    | ({senior_project_id} if senior_project_id else set())
                )

                sem_dict = {
                    'semester': f"{current_semester} {year}",
                    'courses': semester_courses,
                    'total_credits': total_credits,
                }

                # Pass priority so elective padding respects the same
                # ordering preference as the main required course loop
                self._pad_semester_with_electives(
                    sem_dict, exclude_from_padding,
                    max_credits_per_semester, completed, priority
                )

                # Sync back updated values after padding
                semester_courses = sem_dict['courses']
                total_credits = sem_dict['total_credits']

                # Add newly padded electives to all_required so they're treated
                # as scheduled and don't get picked again in a future semester
                for course in semester_courses:
                    all_required.add(course.id)

            # Mark all scheduled courses as completed so next semester's
            # prerequisite checks work correctly
            for course in semester_courses:
                completed.add(course.id)

            # Only publish the semester if it has at least one course
            if semester_courses:
                schedule.append({
                    'semester': f"{current_semester} {year}",
                    'courses': semester_courses,
                    'total_credits': total_credits
                })

            # Alternate Fall → Spring → Fall, incrementing year after each Spring
            if current_semester == 'Fall':
                current_semester = 'Spring'
            else:
                current_semester = 'Fall'
                year += 1

        # ── Place Senior Project in last Fall semester ──────────
        # After all other courses are scheduled, find the last Fall semester
        # that has room within the credit cap and place Senior Project there.
        # If no existing Fall semester has room, create a new dedicated one.
        if reserve_senior_project:
            placed = False

            for sem in reversed(schedule):
                if 'Fall' in sem['semester']:

                    if sem['total_credits'] + senior_project.credits <= max_credits_per_semester:
                        # ✅ Fits within the cap — place Senior Project here
                        sem['courses'].append(senior_project)
                        sem['total_credits'] += senior_project.credits
                        completed.add(senior_project_id)
                        placed = True

                        # Auto-fill if still under minimum after adding Senior Project.
                        # Pass priority so this padding also respects the preference.
                        if sem['total_credits'] < self.MIN_CREDITS_PER_SEMESTER:
                            already_in_sem = {c.id for c in sem['courses']}
                            exclude_from_padding = (
                                all_required
                                | completed
                                | already_in_sem
                                | ({senior_project_id} if senior_project_id else set())
                            )
                            self._pad_semester_with_electives(
                                sem, exclude_from_padding,
                                max_credits_per_semester, completed, priority
                            )
                        break

                    else:
                        # ❌ Adding Senior Project would exceed the cap —
                        # don't force it here, fall through to create a new semester
                        break

            if not placed:
                # No existing Fall semester had room — create a dedicated one
                if schedule:
                    last_sem = schedule[-1]['semester']
                    last_year = int(last_sem.split()[-1])
                    last_season = last_sem.split()[0]
                    # Same year if last was Spring, next year if last was Fall
                    fall_year = last_year if last_season == 'Spring' else last_year + 1
                else:
                    fall_year = year

                new_sem = {
                    'semester': f"Fall {fall_year}",
                    'courses': [senior_project],
                    'total_credits': senior_project.credits,
                }
                completed.add(senior_project_id)

                # Senior Project is only 4cr so this will almost always need padding.
                # Pass priority so even this padding respects the student's preference.
                if new_sem['total_credits'] < self.MIN_CREDITS_PER_SEMESTER:
                    exclude_from_padding = (
                        all_required
                        | completed
                        | ({senior_project_id} if senior_project_id else set())
                    )
                    self._pad_semester_with_electives(
                        new_sem, exclude_from_padding,
                        max_credits_per_semester, completed, priority
                    )

                schedule.append(new_sem)

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