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

    def get_recommendations(self, max_credits: int = 18) -> Dict:
        """
        Get recommended courses for next semester

        Returns:
            {
                'recommended': [courses],
                'total_credits': int,
                'reason': str
            }
        """
        remaining_courses = self._get_remaining_courses()

        # Filter to only courses where prerequisites are met
        eligible_courses = [
            course for course in remaining_courses
            if self._has_prerequisites(course)
        ]

        # Sort by course number (lower numbers = foundational)
        eligible_courses.sort(key=lambda c: c.course_code)

        # Greedy selection: pick courses until we hit credit limit
        recommended = []
        total_credits = 0

        for course in eligible_courses:
            if total_credits + course.credits <= max_credits:
                recommended.append(course)
                total_credits += course.credits

        return {
            'recommended': recommended,
            'total_credits': total_credits,
            'remaining_to_complete': len(remaining_courses) - len(recommended),
        }

    def get_course_details(self, course: Course) -> Dict:
        """Get detailed info about a course including prerequisites"""
        prerequisites = self._get_prerequisites(course)
        prerequisite_courses = Course.objects.filter(id__in=prerequisites)

        return {
            'course': course,
            'prerequisites': list(prerequisite_courses),
            'prerequisites_met': self._has_prerequisites(course),
        }