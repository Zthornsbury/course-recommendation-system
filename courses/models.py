from django.db import models


class Course(models.Model):
    """Represents a course offered by the university"""
    course_code = models.CharField(max_length=20, unique=True)  # e.g., "CSC4899"
    course_name = models.CharField(max_length=200)
    credits = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

    class Meta:
        ordering = ['course_code']


class Prerequisite(models.Model):
    """Represents prerequisite relationships between courses"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prerequisites')
    prerequisite_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='is_prerequisite_for')

    class Meta:
        unique_together = ('course', 'prerequisite_course')

    def __str__(self):
        return f"{self.prerequisite_course.course_code} is a prerequisite for {self.course.course_code}"


class Major(models.Model):
    """Represents a degree major"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    total_credits_required = models.IntegerField()

    def __str__(self):
        return self.name


class Minor(models.Model):
    """Represents a degree minor"""
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    total_credits_required = models.IntegerField()

    def __str__(self):
        return self.name


class DegreeRequirement(models.Model):
    """Represents a requirement for a major/minor"""
    REQUIREMENT_TYPE_CHOICES = [
        ('REQUIRED', 'Required Course'),
        ('ELECTIVE', 'Elective'),
        ('CORE', 'Core Course'),
        ('OPTION', 'Option Group'),
    ]

    major = models.ForeignKey(Major, on_delete=models.CASCADE, related_name='requirements', null=True, blank=True)
    minor = models.ForeignKey(Minor, on_delete=models.CASCADE, related_name='requirements', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_TYPE_CHOICES)
    credits_required = models.IntegerField(default=0)

    def __str__(self):
        if self.major:
            return f"{self.major.name} - {self.requirement_type}"
        return f"{self.minor.name} - {self.requirement_type}"


class Student(models.Model):
    """Represents a student"""
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    major = models.ForeignKey(Major, on_delete=models.SET_NULL, null=True, blank=True)
    minor = models.ForeignKey(Minor, on_delete=models.SET_NULL, null=True, blank=True)
    expected_graduation = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student_id} - {self.first_name} {self.last_name}"


class CompletedCourse(models.Model):
    """Represents a course that a student has completed"""
    GRADE_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('F', 'F'),
        ('P', 'Pass'),
        ('NP', 'No Pass'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='completed_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    date_completed = models.DateField()

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.student_id} - {self.course.course_code}"


class Schedule(models.Model):
    """Represents a recommended semester schedule"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='schedules')
    semester = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    is_optimal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.student_id} - {self.semester}"


class ScheduleCourse(models.Model):
    """Represents a course in a recommended schedule"""
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200, blank=True)  # e.g., "Fulfills major requirement"

    def __str__(self):
        return f"{self.schedule.semester} - {self.course.course_code}"