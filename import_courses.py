import os
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DegreePath.settings')
django.setup()

from courses.models import Course, DegreeRequirement, Major
import PyPDF2


# ============================================================
# CS CORE AND CONCENTRATION COURSES
# ============================================================
ALL_CS_COURSES = [
    # ── Core Required ──────────────────────────────────────
    {'code': 'CSC1980', 'name': 'Exploring Computer Science',                'credits': 2, 'dept': 'Computer Science', 'semester': 'Fall'},
    {'code': 'CSC2280', 'name': 'Introduction to Computer Science',          'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC2290', 'name': 'Object-Oriented Programming',               'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3280', 'name': 'Data Structures',                           'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3310', 'name': 'Computer Organization and Architecture',    'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3380', 'name': 'Algorithms',                                'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3400', 'name': 'Software Engineering',                      'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4410', 'name': 'Operating Systems & Concurrency',           'credits': 4, 'dept': 'Computer Science', 'semester': 'Spring'},
    {'code': 'CSC4899', 'name': 'Senior Project',                            'credits': 4, 'dept': 'Computer Science', 'semester': 'Fall'},
    # ── AI Concentration ───────────────────────────────────
    {'code': 'CSC3510', 'name': 'Introduction to Artificial Intelligence',   'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3520', 'name': 'Machine Learning',                          'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4510', 'name': 'Advanced Topics in Artificial Intelligence','credits': 4, 'dept': 'Computer Science', 'semester': 'Spring'},
    # ── Web Development Concentration ──────────────────────
    {'code': 'CSC3610', 'name': 'Introduction to Web Development',           'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3620', 'name': 'Web Application Architectures',             'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4610', 'name': 'Advanced Topics in Web Development',        'credits': 4, 'dept': 'Computer Science', 'semester': 'Spring'},
    # ── Cybersecurity Concentration ────────────────────────
    {'code': 'CSC3810', 'name': 'Principles of Computer Networking',         'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3820', 'name': 'Penetration Testing and Ethical Hacking',   'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3830', 'name': 'Fundamentals of Digital Forensics',         'credits': 4, 'dept': 'Computer Science', 'semester': 'Fall'},
    {'code': 'CSC4810', 'name': 'Threat Detection Engineering',              'credits': 4, 'dept': 'Computer Science', 'semester': 'Spring'},
    # ── CS Electives ───────────────────────────────────────
    {'code': 'CSC3340', 'name': 'Database Management Systems',               'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3350', 'name': 'Computer Game Design',                      'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC3951', 'name': 'Computer Science Research I',               'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4640', 'name': 'Selected Topics in Computer Science',       'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4645', 'name': 'Selected Topics in CS and Mathematics',     'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4952', 'name': 'Computer Science Research II',              'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'CSC4960', 'name': 'Internship in Computer Science',            'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    # ── Math ───────────────────────────────────────────────
    {'code': 'CSC2100', 'name': 'Discrete Mathematics',                      'credits': 4, 'dept': 'Computer Science', 'semester': 'Both'},
    {'code': 'MAT2022', 'name': 'Elementary Statistics',                     'credits': 4, 'dept': 'Mathematics',      'semester': 'Both'},
    {'code': 'MAT2032', 'name': 'Biostatistics',                             'credits': 4, 'dept': 'Mathematics',      'semester': 'Both'},
    {'code': 'MAT2100', 'name': 'Discrete Mathematics',                      'credits': 4, 'dept': 'Mathematics',      'semester': 'Both'},
    {'code': 'MAT2311', 'name': 'Calculus I with Plane Analytic Geometry',   'credits': 4, 'dept': 'Mathematics',      'semester': 'Both'},
    {'code': 'MAT2312', 'name': 'Calculus II with Plane Analytic Geometry',  'credits': 4, 'dept': 'Mathematics',      'semester': 'Both'},
]

CORE_REQUIRED_CODES = [
    'CSC1980', 'CSC2280', 'CSC2290', 'CSC3280',
    'CSC3310', 'CSC3380', 'CSC3400', 'CSC4410', 'CSC4899',
]

# ============================================================
# WRIGHT FOUNDATION COURSES
# ============================================================
WRIGHT_COURSES = [
    {'code': 'ENG1005', 'name': 'Writing About Topics',                                 'credits': 4, 'dept': 'English',          'semester': 'Both'},
    {'code': 'COM1500', 'name': 'Speak for Success',                                    'credits': 4, 'dept': 'Communication',    'semester': 'Both'},
    {'code': 'DPT2000', 'name': 'Strategic Resilience: Building Strength for Life',    'credits': 2, 'dept': 'General Education', 'semester': 'Both'},
    {'code': 'PSY1106', 'name': 'Psychology and the Social World',                      'credits': 4, 'dept': 'Psychology',       'semester': 'Both'},
    {'code': 'SOC1100', 'name': 'Introduction to Sociology',                            'credits': 4, 'dept': 'Sociology',        'semester': 'Both'},
    {'code': 'HIS1300', 'name': 'The Modern World',                                     'credits': 4, 'dept': 'History',          'semester': 'Both'},
    {'code': 'PHI2304', 'name': 'Ethics',                                               'credits': 4, 'dept': 'Philosophy',       'semester': 'Both'},
    {'code': 'REL2314', 'name': 'Christian Ethics',                                     'credits': 4, 'dept': 'Religion',         'semester': 'Both'},
    {'code': 'ART1100', 'name': 'History of Art and Architecture',                      'credits': 4, 'dept': 'Art',              'semester': 'Both'},
    {'code': 'MUS1101', 'name': 'Chamber Singers',                                      'credits': 4, 'dept': 'Music',            'semester': 'Both'},
    {'code': 'BIO1005', 'name': 'Topics in Biology',                                    'credits': 4, 'dept': 'Biology',          'semester': 'Both'},
    {'code': 'BIO1050', 'name': 'Biology I: Biological Essentials',                     'credits': 4, 'dept': 'Biology',          'semester': 'Both'},
    {'code': 'CHE1050', 'name': 'Principles of Chemistry I',                            'credits': 4, 'dept': 'Chemistry',        'semester': 'Both'},
]

# ============================================================
# GENERAL ELECTIVES — 100+ options from FSC catalog
# Grouped by department for easy browsing on Plan page
# ============================================================
GENERAL_ELECTIVES = [

    # ── Art & Design (fun, creative) ───────────────────────
    {'code': 'ART1110', 'name': 'Introduction to Film',                      'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1120', 'name': 'Design Fundamentals',                       'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1131', 'name': 'Drawing I',                                 'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1140', 'name': 'Introduction to Digital Photography',       'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1150', 'name': 'Principles of Game Design',                 'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1160', 'name': 'New Media',                                 'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART1175', 'name': 'History of Game Design',                    'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2115', 'name': 'Introduction to Digital Filmmaking',        'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2215', 'name': 'Storytelling for the Screen',               'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2225', 'name': 'User Experience Design',                    'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2230', 'name': 'Media Analytics',                           'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2240', 'name': 'Film History',                              'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART2410', 'name': 'Typography and Layout',                     'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART3130', 'name': 'Game Design Scripting',                     'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART3160', 'name': 'Experimental Game Design',                  'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART3275', 'name': 'Special Topics in Game Design',             'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART3510', 'name': 'Web Design',                                'credits': 4, 'dept': 'Art & Design'},
    {'code': 'ART4320', 'name': 'Simulation and Cinematic VR',               'credits': 4, 'dept': 'Art & Design'},

    # ── Astronomy ──────────────────────────────────────────
    {'code': 'AST1010', 'name': 'Descriptive Astronomy',                     'credits': 4, 'dept': 'Astronomy'},

    # ── Biology (interesting topics) ───────────────────────
    {'code': 'BIO1520', 'name': 'Introduction to Marine Biology',            'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO1820', 'name': 'Oceanography',                              'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO1942', 'name': 'Scuba Certification and Ocean Appreciation','credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2120', 'name': 'Biology and Conservation of Marine Mammals','credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2200', 'name': 'Environmental Issues',                      'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2214', 'name': 'Disasters, Civilization and the Environment','credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2215', 'name': 'Human Anatomy and Physiology I',            'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2600', 'name': 'Introduction to Neuroscience',              'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2770', 'name': 'Exercise Physiology',                       'credits': 4, 'dept': 'Biology'},
    {'code': 'BIO2900', 'name': 'Conservation Biology',                      'credits': 4, 'dept': 'Biology'},

    # ── Business ───────────────────────────────────────────
    {'code': 'BUS1115', 'name': 'The Dynamics of Business and Free Enterprise','credits': 4, 'dept': 'Business'},
    {'code': 'BUS2100', 'name': 'Introduction to the Philosophy of Business', 'credits': 4, 'dept': 'Business'},
    {'code': 'BUS2217', 'name': 'Principles of Management',                  'credits': 4, 'dept': 'Business'},
    {'code': 'BUS2220', 'name': 'Microsoft Excel for Business',              'credits': 4, 'dept': 'Business'},
    {'code': 'BUS2860', 'name': 'Professional Development',                  'credits': 4, 'dept': 'Business'},
    {'code': 'BUS3200', 'name': 'Organizational Behavior',                   'credits': 4, 'dept': 'Business'},
    {'code': 'BUS3311', 'name': 'Legal Environment of Business',             'credits': 4, 'dept': 'Business'},
    {'code': 'BUS3320', 'name': 'Applied Statistics and Analytics for Business','credits': 4, 'dept': 'Business'},
    {'code': 'BUS3650', 'name': 'Project Management',                        'credits': 4, 'dept': 'Business'},
    {'code': 'BUS3666', 'name': 'Leadership Competencies',                   'credits': 4, 'dept': 'Business'},
    {'code': 'BUS4110', 'name': 'Law in Film I: Legal Issues and Procedures','credits': 4, 'dept': 'Business'},
    {'code': 'BUS4120', 'name': 'Law in Film II: Ethics and Perceptions',    'credits': 4, 'dept': 'Business'},
    {'code': 'BUS4420', 'name': 'Business Analytics',                        'credits': 4, 'dept': 'Business'},
    {'code': 'BUS4440', 'name': 'Data Mining',                               'credits': 4, 'dept': 'Business'},
    {'code': 'BUS4450', 'name': 'Data Visualization',                        'credits': 4, 'dept': 'Business'},

    # ── Communication ──────────────────────────────────────
    {'code': 'COM1100', 'name': 'Introduction to Communication',             'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2100', 'name': 'Mass Media and Society',                    'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2110', 'name': 'Media Writing',                             'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2150', 'name': 'Media in Sport',                            'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2250', 'name': 'Interpersonal Communication',               'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2270', 'name': 'Intercultural Communication',               'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2340', 'name': 'Introduction to Video Production',          'credits': 4, 'dept': 'Communication'},
    {'code': 'COM2400', 'name': 'Principles of Advertising and Public Relations','credits': 4, 'dept': 'Communication'},
    {'code': 'COM2500', 'name': 'Visual Communication',                      'credits': 4, 'dept': 'Communication'},
    {'code': 'COM3200', 'name': 'Persuasion',                                'credits': 4, 'dept': 'Communication'},
    {'code': 'COM3360', 'name': 'Online Media',                              'credits': 4, 'dept': 'Communication'},
    {'code': 'COM3370', 'name': 'Photojournalism',                           'credits': 4, 'dept': 'Communication'},
    {'code': 'COM3905', 'name': 'Politics and the Media',                    'credits': 4, 'dept': 'Communication'},
    {'code': 'COM4350', 'name': 'Social Media Strategies',                   'credits': 4, 'dept': 'Communication'},
    {'code': 'COM4500', 'name': 'Communication Law and Ethics',              'credits': 4, 'dept': 'Communication'},

    # ── Criminology ────────────────────────────────────────
    {'code': 'CRM1280', 'name': 'Introduction to Criminal Justice',          'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM2350', 'name': 'Policing in American Society',              'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM2430', 'name': 'Ethics in Criminal Justice',                'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM3310', 'name': 'Crime Scene Investigation',                 'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM3340', 'name': 'Criminology',                               'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM3360', 'name': 'Juvenile Delinquency',                      'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM4440', 'name': 'Judicial Processes',                        'credits': 4, 'dept': 'Criminology'},
    {'code': 'CRM4450', 'name': 'Corrections and Rehabilitation',            'credits': 4, 'dept': 'Criminology'},

    # ── Economics ──────────────────────────────────────────
    {'code': 'ECO2010', 'name': 'Essentials of Economics',                   'credits': 4, 'dept': 'Economics'},
    {'code': 'ECO2205', 'name': 'Principles of Microeconomics',              'credits': 4, 'dept': 'Economics'},
    {'code': 'ECO2207', 'name': 'Principles of Macroeconomics',              'credits': 4, 'dept': 'Economics'},
    {'code': 'ECO3345', 'name': 'Economics and the Environment',             'credits': 4, 'dept': 'Economics'},
    {'code': 'ECO4200', 'name': 'Behavioral Economics',                      'credits': 4, 'dept': 'Economics'},
    {'code': 'ECO4300', 'name': 'Introduction to Econometrics',              'credits': 4, 'dept': 'Economics'},

    # ── English ────────────────────────────────────────────
    {'code': 'ENG1130', 'name': 'Introduction to Literary Studies',          'credits': 4, 'dept': 'English'},
    {'code': 'ENG2100', 'name': 'Technical Writing',                         'credits': 4, 'dept': 'English'},
    {'code': 'ENG3219', 'name': 'Persuasive Writing',                        'credits': 4, 'dept': 'English'},

    # ── Mathematics (advanced) ─────────────────────────────
    {'code': 'MAT3311', 'name': 'Calculus III',                              'credits': 4, 'dept': 'Mathematics'},
    {'code': 'MAT3320', 'name': 'Linear Algebra',                            'credits': 4, 'dept': 'Mathematics'},
    {'code': 'MAT3330', 'name': 'Differential Equations',                    'credits': 4, 'dept': 'Mathematics'},
    {'code': 'MAT4410', 'name': 'Numerical Analysis',                        'credits': 4, 'dept': 'Mathematics'},

    # ── Philosophy ─────────────────────────────────────────
    {'code': 'PHI2200', 'name': 'Introduction to Logic',                     'credits': 4, 'dept': 'Philosophy'},
    {'code': 'PHI3310', 'name': 'Philosophy of Mind',                        'credits': 4, 'dept': 'Philosophy'},

    # ── Physics ────────────────────────────────────────────
    {'code': 'PHY2110', 'name': 'General Physics I (Calculus Based)',        'credits': 4, 'dept': 'Physics'},
    {'code': 'PHY2120', 'name': 'General Physics II (Calculus Based)',       'credits': 4, 'dept': 'Physics'},

    # ── Psychology ─────────────────────────────────────────
    {'code': 'PSY2200', 'name': 'Cognitive Psychology',                      'credits': 4, 'dept': 'Psychology'},
    {'code': 'PSY2210', 'name': 'Abnormal Psychology',                       'credits': 4, 'dept': 'Psychology'},
    {'code': 'PSY3100', 'name': 'Critical Thinking in Social and Behavioral Sciences','credits': 4, 'dept': 'Psychology'},
    {'code': 'PSY3310', 'name': 'Human Factors and Ergonomics',              'credits': 4, 'dept': 'Psychology'},
    {'code': 'PSY3380', 'name': 'Professional Development in Behavioral Sciences','credits': 4, 'dept': 'Psychology'},

    # ── Sociology ──────────────────────────────────────────
    {'code': 'SOC2220', 'name': 'Marriage and Family',                       'credits': 4, 'dept': 'Sociology'},
    {'code': 'SOC2240', 'name': 'Clinical Sociology',                        'credits': 4, 'dept': 'Sociology'},
    {'code': 'SOC3303', 'name': 'Sociology of Deviant Behavior',             'credits': 4, 'dept': 'Sociology'},
]

# ============================================================
# DESCRIPTIONS
# ============================================================
CS_DESCRIPTIONS = {
    'CSC1980': 'Explore topics in computer science, including ethical and societal implications of advances in computing technology.',
    'CSC2280': 'Concepts of algorithmic thinking, computer programming, machine organization and selected current topics in computer science.',
    'CSC2290': 'Introduction to object-oriented programming. Topics include classes, inheritance, polymorphism, and exception handling.',
    'CSC2100': 'Introduction to discrete mathematics including logic, set theory, proofs, induction, recursion, counting, and probability.',
    'CSC3280': 'Design and implementation of data structures including lists, stacks, queues, trees, graphs, and hash tables.',
    'CSC3310': 'Organization and architecture of computer systems including digital logic, data representation, and assembly language.',
    'CSC3340': 'Database systems including relational model, SQL, database design, normalization, and transaction management.',
    'CSC3350': 'Storyboarding, technology, science, and graphics in computer game creation. Emphasis on hands-on design.',
    'CSC3380': 'Design and analysis of algorithms including sorting, searching, graph algorithms, and computational complexity.',
    'CSC3400': 'Software engineering principles including requirements analysis, design patterns, testing, and version control.',
    'CSC3510': 'Introduction to artificial intelligence including search algorithms, knowledge representation, and machine learning.',
    'CSC3520': 'Machine learning algorithms including supervised learning, unsupervised learning, and neural networks.',
    'CSC3610': 'Introduction to web development including HTML, CSS, JavaScript, and server-side frameworks.',
    'CSC3620': 'Advanced web application development including RESTful APIs, frameworks, and deployment.',
    'CSC3810': 'Computer networking including architectures, protocols, TCP/IP, routing, and security fundamentals.',
    'CSC3820': 'Penetration testing methodologies, ethical hacking techniques, and vulnerability assessment.',
    'CSC3830': 'Digital forensics including evidence collection, file system analysis, and network forensics.',
    'CSC3951': 'Introduction to computer science research. Students work with faculty on ongoing projects. Requires 3.0 GPA.',
    'CSC4410': 'Operating system components including processes, scheduling, concurrency, and memory management.',
    'CSC4510': 'Advanced artificial intelligence including evolutionary computation, neural networks, and planning.',
    'CSC4610': 'Advanced web development including modern frameworks, microservices, and cloud deployment.',
    'CSC4640': 'Selected advanced topics in computer science. Content varies based on current developments.',
    'CSC4645': 'Selected advanced topics at the intersection of computer science and mathematics.',
    'CSC4810': 'Cybersecurity including threat detection, incident response, and enterprise security architecture.',
    'CSC4899': 'Capstone senior project demonstrating mastery of computer science concepts.',
    'CSC4952': 'Advanced undergraduate research in computer science under faculty supervision.',
    'CSC4960': 'Professional internship experience in computer science industry or research settings.',
    'MAT2022': 'Statistical methods including data collection, descriptive statistics, probability, and inference.',
    'MAT2032': 'Biostatistical methods including hypothesis testing, regression, and analysis of variance.',
    'MAT2100': 'Discrete mathematics including logic, set theory, proofs, induction, and probability.',
    'MAT2311': 'Differential and integral calculus including limits, derivatives, integrals, and applications.',
    'MAT2312': 'Continuation of Calculus I including integration techniques, infinite series, and analytic geometry.',
}

WRIGHT_DESCRIPTIONS = {
    'ART1100': 'History and theory of art and architecture from ancient civilizations to the modern era.',
    'BIO1005': 'Introduction to biology including cell biology, genetics, evolution, and ecology.',
    'BIO1050': 'Fundamental biological concepts including cell structure, metabolism, genetics, and diversity of life.',
    'CHE1050': 'Principles of chemistry including atomic structure, chemical bonding, reactions, and stoichiometry.',
    'COM1500': 'Public speaking and oral communication through speeches, group discussion, and presentations.',
    'DPT2000': 'Building personal resilience, stress management, and life skills for academic and professional success.',
    'ENG1005': 'Written communication skills through analysis and composition focused on clarity and argumentation.',
    'HIS1300': 'Survey of modern world history examining political, social, economic, and cultural developments.',
    'MUS1101': 'College choir ensemble developing vocal technique, music reading, and performance skills.',
    'PHI2304': 'Major ethical theories applied to contemporary moral issues including justice, rights, and virtue.',
    'PSY1106': 'Psychological principles applied to human behavior including perception, motivation, and social influence.',
    'REL2314': 'Christian ethical principles and their application to contemporary moral and social issues.',
    'SOC1100': 'Sociological concepts examining social institutions, culture, stratification, and social change.',
}

ELECTIVE_DESCRIPTIONS = {
    # Art & Design
    'ART1110': 'Introduction to film as an art form including narrative, documentary, and experimental film genres.',
    'ART1120': 'Fundamentals of visual design including color theory, composition, typography, and digital tools.',
    'ART1131': 'Basic drawing techniques including line, form, perspective, shading, and composition.',
    'ART1140': 'Digital photography fundamentals including camera operation, composition, lighting, and editing.',
    'ART1150': 'Introduction to game design principles including mechanics, player experience, and prototyping.',
    'ART1160': 'Exploration of new and emerging media including interactive art, net art, and digital installation.',
    'ART1175': 'Survey of game design history from early arcade games to modern interactive entertainment.',
    'ART2115': 'Introduction to digital filmmaking including pre-production, shooting, editing, and distribution.',
    'ART2215': 'Principles of narrative storytelling for film, television, and interactive media.',
    'ART2225': 'User experience design principles including research, wireframing, prototyping, and usability testing.',
    'ART2230': 'Analytical methods for measuring media audiences, content performance, and digital engagement.',
    'ART2240': 'Survey of film history from silent cinema through contemporary international cinema.',
    'ART2410': 'Typography and layout principles for print and digital media design.',
    'ART3130': 'Programming and scripting for interactive game design using industry-standard tools.',
    'ART3160': 'Experimental approaches to game design exploring non-traditional mechanics and player experiences.',
    'ART3275': 'Advanced topics in game design including level design, game writing, and production pipelines.',
    'ART3510': 'Web design principles including HTML, CSS, user interface design, and web accessibility.',
    'ART4320': 'Virtual reality and cinematic VR production including 360-degree video and immersive storytelling.',
    # Astronomy
    'AST1010': 'Introduction to astronomy covering the solar system, stars, galaxies, and the universe.',
    # Biology
    'BIO1520': 'Introduction to marine biology including ocean ecosystems, marine organisms, and conservation.',
    'BIO1820': 'Oceanography covering ocean circulation, marine geology, chemistry, and climate interactions.',
    'BIO1942': 'Scuba certification course combined with study of ocean ecology and marine conservation.',
    'BIO2120': 'Biology, behavior, and conservation of marine mammals including whales, dolphins, and seals.',
    'BIO2200': 'Environmental issues including climate change, pollution, biodiversity loss, and sustainability.',
    'BIO2214': 'How natural disasters and environmental changes have shaped human civilizations throughout history.',
    'BIO2215': 'Human anatomy and physiology covering cells, tissues, organs, and organ systems.',
    'BIO2600': 'Introduction to neuroscience including brain structure, neural communication, and behavior.',
    'BIO2770': 'Physiological responses to exercise including cardiovascular, respiratory, and metabolic adaptations.',
    'BIO2900': 'Principles of conservation biology including biodiversity, habitat loss, and species recovery.',
    # Business
    'BUS1115': 'Overview of business functions, free market economics, and entrepreneurial thinking.',
    'BUS2100': 'Philosophical foundations of business ethics, capitalism, and organizational decision-making.',
    'BUS2217': 'Management principles including planning, organizing, leading, and controlling organizations.',
    'BUS2220': 'Microsoft Excel skills for business analysis including formulas, charts, and pivot tables.',
    'BUS2860': 'Professional development skills including resume writing, interviewing, and career planning.',
    'BUS3200': 'Organizational behavior including motivation, leadership, teamwork, and organizational culture.',
    'BUS3311': 'Legal environment of business including contracts, torts, employment law, and regulations.',
    'BUS3320': 'Statistical and analytical methods applied to business decision making and data analysis.',
    'BUS3650': 'Project management methodologies including planning, scheduling, budgeting, and risk management.',
    'BUS3666': 'Leadership theories and competencies for organizational effectiveness and personal development.',
    'BUS4110': 'Legal issues and procedures in business examined through landmark film portrayals.',
    'BUS4120': 'Business ethics and professional conduct examined through film portrayals and case studies.',
    'BUS4420': 'Business analytics including descriptive, predictive, and prescriptive analytical methods.',
    'BUS4440': 'Data mining techniques for discovering patterns and knowledge from large datasets.',
    'BUS4450': 'Data visualization principles and tools for communicating insights from complex datasets.',
    # Communication
    'COM1100': 'Introduction to communication theory and practice across interpersonal and mass media contexts.',
    'COM2100': 'Survey of mass media including print, broadcast, digital media, and their societal impact.',
    'COM2110': 'Writing for various media platforms including news, features, and digital content.',
    'COM2150': 'Role of media in sports including broadcasting, social media, and sports journalism.',
    'COM2250': 'Interpersonal communication including listening, conflict resolution, and relationship development.',
    'COM2270': 'Communication across cultures including cultural differences, identity, and global communication.',
    'COM2340': 'Introduction to video production including pre-production, shooting, editing, and distribution.',
    'COM2400': 'Principles of advertising and public relations including strategy, messaging, and campaigns.',
    'COM2500': 'Visual communication principles including graphic design, photography, and visual rhetoric.',
    'COM3200': 'Persuasion theory and practice including argument, rhetoric, and attitude change.',
    'COM3360': 'Online media platforms including digital journalism, social media, and web content creation.',
    'COM3370': 'Photojournalism including visual storytelling, ethics, and digital image production.',
    'COM3905': 'Relationship between politics and media including news framing, political advertising, and bias.',
    'COM4350': 'Social media strategy including platform analysis, content creation, and audience engagement.',
    'COM4500': 'Communication law and ethics including First Amendment, privacy, and professional standards.',
    # Criminology
    'CRM1280': 'Overview of the criminal justice system including law enforcement, courts, and corrections.',
    'CRM2350': 'History and practice of policing including community policing and law enforcement ethics.',
    'CRM2430': 'Ethical issues in criminal justice including use of force, corruption, and justice reform.',
    'CRM3310': 'Crime scene investigation techniques including evidence collection and forensic analysis.',
    'CRM3340': 'Theories of criminal behavior and sociological perspectives on crime and deviance.',
    'CRM3360': 'Causes and consequences of juvenile delinquency and the juvenile justice system.',
    'CRM4440': 'Judicial processes including courts, prosecution, defense, and sentencing.',
    'CRM4450': 'Corrections and rehabilitation including prisons, probation, and reentry programs.',
    # Economics
    'ECO2010': 'Introduction to economic principles including supply and demand, markets, and policy.',
    'ECO2205': 'Microeconomics including consumer behavior, firm theory, market structures, and welfare.',
    'ECO2207': 'Macroeconomics including national income, unemployment, inflation, and fiscal policy.',
    'ECO3345': 'Environmental economics including market failures, externalities, and sustainability policy.',
    'ECO4200': 'Behavioral economics exploring how psychology influences economic decisions and markets.',
    'ECO4300': 'Introduction to econometrics including regression analysis and statistical modeling.',
    # English
    'ENG1130': 'Introduction to literary analysis including poetry, fiction, drama, and critical methods.',
    'ENG2100': 'Technical writing for professional contexts including documentation, reports, and proposals.',
    'ENG3219': 'Advanced persuasive writing for professional and public contexts.',
    # Mathematics
    'MAT3311': 'Multivariable calculus including partial derivatives, multiple integrals, and vector calculus.',
    'MAT3320': 'Linear algebra including vectors, matrices, linear transformations, and eigenvalues.',
    'MAT3330': 'Ordinary differential equations including first and second order equations and applications.',
    'MAT4410': 'Numerical methods for solving mathematical problems computationally.',
    # Philosophy
    'PHI2200': 'Formal and informal logic including argument analysis, fallacies, and deductive reasoning.',
    'PHI3310': 'Philosophy of mind including consciousness, mental states, and artificial intelligence.',
    # Physics
    'PHY2110': 'Calculus-based physics covering mechanics, thermodynamics, and waves.',
    'PHY2120': 'Calculus-based physics covering electricity, magnetism, optics, and modern physics.',
    # Psychology
    'PSY2200': 'Mental processes including perception, attention, memory, language, and problem solving.',
    'PSY2210': 'Psychological disorders including classification, causes, and treatment approaches.',
    'PSY3100': 'Critical thinking and research methods in social and behavioral sciences.',
    'PSY3310': 'Human factors and ergonomics including human-computer interaction and system design.',
    'PSY3380': 'Professional development skills for careers in social and behavioral sciences.',
    # Sociology
    'SOC2220': 'Sociological study of marriage, family structures, relationships, and social change.',
    'SOC2240': 'Applied sociology addressing social problems through clinical and community interventions.',
    'SOC3303': 'Sociological perspectives on deviant behavior, social norms, and social control.',
}


def extract_csc_courses_from_pdf(pdf_path):
    """Extract CSC course descriptions from the catalog PDF"""
    print("Extracting CSC courses from PDF...")
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        full_text = ""
        for i in range(242, 246):
            if i < len(pdf_reader.pages):
                full_text += pdf_reader.pages[i].extract_text()

        full_text = re.sub(r'FLORIDA SOUTHERN COLLEGE \d+', '', full_text)
        full_text = re.sub(r'UNDERGRADUATE COURSE DESCRIPTIONS \d+', '', full_text)

        courses = []
        pattern = r'CSC\s+(\d+)\s+([A-Z][A-Z\s\-/]+?)\n(.*?)(?=\nCSC\s+\d+|$)'
        matches = re.findall(pattern, full_text, re.DOTALL)

        for match in matches:
            course_number = match[0].strip()
            course_name = match[1].strip()
            details = match[2].strip()

            credits_match = re.search(r'(Two|Three|Four)\s+hours?', details)
            credits = {'Two': 2, 'Three': 3, 'Four': 4}.get(
                credits_match.group(1), 4) if credits_match else 4

            description = re.sub(r'^(Two|Three|Four)\s+hours?\.\s*', '', details)
            description = ' '.join(description.split())
            description = re.sub(r'FLORIDA SOUTHERN COLLEGE \d+', '', description).strip()

            if len(description) < 10:
                description = f"A {credits}-credit Computer Science course."
            if len(description) > 500:
                description = description[:500].rsplit(' ', 1)[0] + '...'
            if description and not description.endswith('.'):
                description += '.'

            courses.append({
                'code': f'CSC{course_number}',
                'name': course_name,
                'credits': credits,
                'description': description,
                'semester': 'Both'
            })
        return courses


def import_all_courses():
    """Import all courses into the database"""

    # Try PDF extraction for CS course descriptions
    pdf_path = 'fsc-catalog.pdf'
    pdf_courses = []
    if os.path.exists(pdf_path):
        pdf_courses = extract_csc_courses_from_pdf(pdf_path)
        print(f"Found {len(pdf_courses)} CS courses from PDF\n")
    else:
        print("PDF not found — using manual data only\n")

    pdf_lookup = {c['code']: c for c in pdf_courses}

    # ── Step 1: CS and math courses ────────────────────────────
    print("=" * 60)
    print("IMPORTING CS AND MATH COURSES")
    print("=" * 60)

    for c in ALL_CS_COURSES:
        description = CS_DESCRIPTIONS.get(c['code'])
        if not description and c['code'] in pdf_lookup:
            description = pdf_lookup[c['code']]['description']
        if not description:
            description = f"Computer Science course: {c['name']}."

        course, created = Course.objects.update_or_create(
            course_code=c['code'],
            defaults={
                'course_name': c['name'],
                'credits': c['credits'],
                'description': description,
                'department': c['dept'],
                'semester_offered': c['semester'],
            }
        )
        print(f"{'✓ Created' if created else '↺ Updated'}: {course.course_code} - {course.course_name}")

    # ── Step 2: WRIGHT Foundation courses ──────────────────────
    print("\n" + "=" * 60)
    print("IMPORTING WRIGHT FOUNDATION COURSES")
    print("=" * 60)

    for c in WRIGHT_COURSES:
        description = WRIGHT_DESCRIPTIONS.get(c['code'], f"WRIGHT Foundation requirement in {c['dept']}.")
        course, created = Course.objects.update_or_create(
            course_code=c['code'],
            defaults={
                'course_name': c['name'],
                'credits': c['credits'],
                'description': description,
                'department': c['dept'],
                'semester_offered': c['semester'],
            }
        )
        print(f"{'✓ Created' if created else '↺ Updated'}: {course.course_code} - {course.course_name}")

    # ── Step 3: General electives ───────────────────────────────
    print("\n" + "=" * 60)
    print(f"IMPORTING {len(GENERAL_ELECTIVES)} GENERAL ELECTIVES")
    print("=" * 60)

    for c in GENERAL_ELECTIVES:
        description = ELECTIVE_DESCRIPTIONS.get(c['code'], f"Elective course in {c['dept']}.")
        course, created = Course.objects.update_or_create(
            course_code=c['code'],
            defaults={
                'course_name': c['name'],
                'credits': c['credits'],
                'description': description,
                'department': c['dept'],
                'semester_offered': 'Both',
            }
        )
        print(f"{'✓ Created' if created else '↺ Updated'}: {course.course_code} - {course.course_name}")

    # ── Step 4: Degree requirements ─────────────────────────────
    print("\n" + "=" * 60)
    print("SETTING UP DEGREE REQUIREMENTS")
    print("=" * 60)

    try:
        csc_major = Major.objects.get(code='CSC')

        # Core CS required courses
        for code in CORE_REQUIRED_CODES:
            try:
                course = Course.objects.get(course_code=code)
                req, created = DegreeRequirement.objects.get_or_create(
                    major=csc_major,
                    course=course,
                    defaults={'requirement_type': 'REQUIRED', 'credits_required': course.credits}
                )
                print(f"{'✓ Added' if created else '  Exists'}: {code}")
            except Course.DoesNotExist:
                print(f"⚠ Not found: {code}")

        # WRIGHT Foundation courses
        for c in WRIGHT_COURSES:
            try:
                course = Course.objects.get(course_code=c['code'])
                req, created = DegreeRequirement.objects.get_or_create(
                    major=csc_major,
                    course=course,
                    defaults={'requirement_type': 'REQUIRED', 'credits_required': course.credits}
                )
                print(f"{'✓ Added' if created else '  Exists'}: {c['code']}")
            except Course.DoesNotExist:
                print(f"⚠ Not found: {c['code']}")

        print("\n  Note: General electives are added to the catalog only.")
        print("  Students choose them freely on the Plan page.")
        print("\n✅ ALL DONE!")

    except Major.DoesNotExist:
        print("\n⚠️  ERROR: CSC Major not found. Create it in the admin panel first.")


if __name__ == '__main__':
    import_all_courses()
    print("\n✅ Import complete!")