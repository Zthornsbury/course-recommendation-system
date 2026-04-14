# ============================================================
# course_config.py
# Located at: courses/course_config.py
#
# This file maps all CSC course prerequisites based on the
# Florida Southern College academic catalog.
#
# Structure:
#   COURSE_PREREQUISITES = {
#       'COURSE_CODE': ['PREREQ_CODE', 'PREREQ_CODE', ...],
#   }
#
# An empty list means the course has no prerequisites.
# ============================================================

COURSE_PREREQUISITES = {

    # ── No prerequisites ─────────────────────────────────────
    'CSC1980': [],   # Computer Science Freshman Seminar
    'CSC2280': [],   # Introduction to Computer Science
    'MAT2022': [],   # Elementary Statistics
    'MAT2032': [],   # Biostatistics
    'MAT2311': [],   # Calculus I with Plane Analytic Geometry

    # ── 2000-level CSC ───────────────────────────────────────
    'CSC2100': [],          # Discrete Mathematics (also listed as MAT2100)
    'CSC2290': ['CSC2280'], # Object-Oriented Programming → requires CSC2280

    # ── 3000-level CSC ───────────────────────────────────────
    'CSC3280': ['CSC2290'],             # Data Structures → requires CSC2290
    'CSC3310': ['CSC2290'],             # Computer Organization & Architecture → requires CSC2290 or sophomore standing
    'CSC3340': ['CSC2290'],             # Database Management Systems → requires CSC2290
    'CSC3350': ['CSC2290'],             # Computer Game Design → requires CSC2290
    'CSC3380': ['CSC2100', 'CSC3280'],  # Algorithms → requires CSC/MAT2100 AND CSC3280
    'CSC3400': ['CSC3280'],             # Software Engineering → requires CSC3280
    'CSC3510': ['CSC2290'],             # Introduction to Artificial Intelligence → requires CSC2290
    'CSC3520': ['CSC3510'],             # Machine Learning → requires CSC3510
    'CSC3610': ['CSC2290'],             # Introduction to Web Development → requires CSC2290
    'CSC3620': ['CSC3610'],             # Web Application Architectures → requires CSC3610
    'CSC3810': ['CSC2280'],             # Principles of Computer Networking → requires CSC2280
    'CSC3820': ['CSC3810'],             # Penetration Testing & Ethical Hacking → requires CSC3810
    'CSC3830': ['CSC3810'],             # Fundamentals of Digital Forensics → requires CSC3810

    # ── 3951 Research I ──────────────────────────────────────
    'CSC3951': ['CSC3380'],  # Computer Science Research I → requires CSC3380, instructor permission, min 3.0 GPA

    # ── 4000-level CSC ───────────────────────────────────────
    'CSC4410': ['CSC2290', 'CSC3310'],  # Operating Systems & Concurrency → requires CSC2290 AND CSC3310
    'CSC4510': ['CSC3520'],             # Advanced Topics in AI → requires CSC3520
    'CSC4610': ['CSC3620'],             # Advanced Topics in Web Development → requires CSC3620
    'CSC4640': ['CSC2290'],             # Selected Topics in CS → requires CSC2290 or instructor permission
    'CSC4645': ['CSC2290'],             # Selected Topics in CS and Mathematics → requires CSC2290 or instructor permission
    'CSC4810': ['CSC3810'],             # Threat Detection Engineering → requires CSC3810
    'CSC4899': ['CSC3400'],             # Senior Project → requires CSC3400

    # ── 4952 Research II ─────────────────────────────────────
    'CSC4952': ['CSC3951'],  # Computer Science Research II → requires CSC3951, senior standing, min 3.0 GPA

    # ── Internship ───────────────────────────────────────────
    'CSC4960': [],  # Internship → requires instructor permission and min 2.5 GPA (no course prereqs)

    # ── Math requirements ────────────────────────────────────
    'MAT2100': [],           # Discrete Mathematics (same as CSC2100)
    'MAT2312': ['MAT2311'],  # Calculus II → requires MAT2311
}


# ============================================================
# DEGREE REQUIREMENTS
# Core required courses for the CS major
# ============================================================

CS_CORE_REQUIRED = [
    'CSC1980',
    'CSC2280',
    'CSC2290',
    'CSC3280',
    'CSC3310',
    'CSC3380',
    'CSC3400',
    'CSC4410',
    'CSC4899',
]

# Concentration tracks (student picks ONE)
CS_CONCENTRATION_AI = ['CSC3510', 'CSC3520', 'CSC4510']
CS_CONCENTRATION_WEB = ['CSC3610', 'CSC3620', 'CSC4610']
CS_CONCENTRATION_CYBER = ['CSC3810', 'CSC3820', 'CSC3830', 'CSC4810']

# General electives pool (if no concentration chosen)
CS_ELECTIVES = [
    'CSC3340', 'CSC3350', 'CSC3510', 'CSC3520',
    'CSC3610', 'CSC3620', 'CSC3810', 'CSC3820',
    'CSC3830', 'CSC3951', 'CSC4510', 'CSC4640',
]

# Math requirements
CS_MATH_REQUIRED = ['CSC2100']  # Discrete Mathematics
CS_MATH_OPTIONS = ['MAT2022', 'MAT2032']  # Statistics (pick one)