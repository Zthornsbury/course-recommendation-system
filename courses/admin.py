from django.contrib import admin
from .models import (
    Course, Prerequisite, Major, Minor, DegreeRequirement,
    Student, CompletedCourse, Schedule, ScheduleCourse
)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'credits', 'department')
    search_fields = ('course_code', 'course_name')
    list_filter = ('department', 'credits')

@admin.register(Prerequisite)
class PrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('prerequisite_course', 'course')
    search_fields = ('course__course_code', 'prerequisite_course__course_code')

@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'total_credits_required')
    search_fields = ('name', 'code')

@admin.register(Minor)
class MinorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'total_credits_required')
    search_fields = ('name', 'code')

@admin.register(DegreeRequirement)
class DegreeRequirementAdmin(admin.ModelAdmin):
    list_display = ('requirement_type', 'major', 'minor', 'credits_required')
    list_filter = ('requirement_type', 'major', 'minor')
    search_fields = ('major__name', 'minor__name')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'email', 'major')
    search_fields = ('student_id', 'first_name', 'last_name', 'email')
    list_filter = ('major', 'minor')

@admin.register(CompletedCourse)
class CompletedCourseAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'semester', 'grade', 'date_completed')
    search_fields = ('student__student_id', 'course__course_code')
    list_filter = ('semester', 'grade')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'created_at', 'is_optimal')
    search_fields = ('student__student_id', 'semester')
    list_filter = ('semester', 'is_optimal')

@admin.register(ScheduleCourse)
class ScheduleCourseAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'course', 'reason')
    search_fields = ('schedule__student__student_id', 'course__course_code')
