from courses.models import Course, CompletedCourse, Prerequisite, DegreeRequirement, Major
from typing import List, Dict, Set


class CourseRecommender:
    """
    Recommends courses for a student based on:
    - Completed courses
    - Prerequisites
    - Credit limits (max 18 per semester)
    - Degree requirements
    """

    def __init__(self, student):
        self.student = student
        self.completed_courses = self._get_completed_courses()
        self.major = student.major

    def _get_completed_courses(self) -> Set[int]:
        """Get set of course IDs the student has completed"""
        return set(
            CompletedCourse.objects
            .filter(student=self.student)
            .values_list('course_id', flat=True)
        )

    def _get_prerequisites(self, course: Course) -> Set[int]:
        """Get all prerequisite course IDs for a given course"""
        return set(
            Prerequisite.objects
            .filter(course=course)
            .values_list('prerequisite_course_id', flat=True)
        )

    def _has_prerequisites(self, course: Course) -> bool:
        """Check if student has completed all prerequisites for a course"""
        required_prerequisites = self._get_prerequisites(course)
        return required_prerequisites.issubset(self.completed_courses)

    def _get_required_courses_for_major(self) -> List[Course]:
        """Get all required courses for the student's major"""
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

    def _get_remaining_courses(self) -> List[Course]:
        """Get courses student still needs to take"""
        required_courses = self._get_required_courses_for_major()
        return [c for c in required_courses if c.id not in self.completed_courses]

    def get_full_schedule(self, max_credits_per_semester=18):
        """
        Generate a complete semester-by-semester schedule until graduation.
        Returns a list of semesters with recommended courses.
        """
        schedule = []
        completed = self.completed_courses.copy()
        current_semester = 'Fall'  # Start with Fall
        semester_count = 0
        max_semesters = 10  # Safety limit to prevent infinite loops
        year = 2026  # Starting year

        # Get all required courses
        all_required = set(
            DegreeRequirement.objects
            .filter(major=self.major)
            .values_list('course_id', flat=True)
        )

        while semester_count < max_semesters:
            semester_count += 1

            # Check if we're done FIRST
            if completed >= all_required:
                break

            # Get available courses for this semester
            available_courses = Course.objects.filter(
                id__in=all_required - completed,
                semester_offered__in=[current_semester, 'Both']
            )

            # Filter by prerequisites
            semester_courses = []
            total_credits = 0

            for course in available_courses:
                if self._has_prerequisites_from_set(course, completed):
                    if total_credits + course.credits <= max_credits_per_semester:
                        semester_courses.append(course)
                        total_credits += course.credits
                        completed.add(course.id)

            # Add semester to schedule if there are courses
            if semester_courses:
                schedule.append({
                    'semester': f"{current_semester} {year}",
                    'courses': semester_courses,
                    'total_credits': total_credits
                })

            # Toggle semester and increment year
            if current_semester == 'Fall':
                current_semester = 'Spring'
            else:
                current_semester = 'Fall'
                year += 1

        return {
            'schedule': schedule,
            'total_semesters': len(schedule),  # FIXED: Use actual schedule length
            'courses_remaining': len(all_required - completed)
        }

    def _has_prerequisites_from_set(self, course, completed_set):
        """Check if prerequisites are met from a given set of completed courses"""
        prerequisites = self._get_prerequisites(course)
        return prerequisites.issubset(completed_set)

    def get_course_details(self, course: Course) -> Dict:
        """Get detailed info about a course including prerequisites"""
        prerequisites = self._get_prerequisites(course)
        prerequisite_courses = Course.objects.filter(id__in=prerequisites)

        return {
            'course': course,
            'prerequisites': list(prerequisite_courses),
            'prerequisites_met': self._has_prerequisites(course),
        }