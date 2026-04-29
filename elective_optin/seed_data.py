# -*- coding: utf-8 -*-
"""
OptiSeat - Rich demo seed data
Run: python seed_data.py  (from elective_optin/ directory)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from electives.models import Department, Course, Student, Preference, StudentCourseHistory


def populate():
    print("[*] Seeding OptiSeat demo data...")

    # --- DEPARTMENTS ---
    cse,   _ = Department.objects.get_or_create(code='CSE',   defaults={'name': 'Computer Science & Engineering'})
    ece,   _ = Department.objects.get_or_create(code='ECE',   defaults={'name': 'Electronics & Communication'})
    me,    _ = Department.objects.get_or_create(code='ME',    defaults={'name': 'Mechanical Engineering'})
    civil, _ = Department.objects.get_or_create(code='CIVIL', defaults={'name': 'Civil Engineering'})
    mba,   _ = Department.objects.get_or_create(code='MBA',   defaults={'name': 'Business Administration'})
    is_,   _ = Department.objects.get_or_create(code='IS',    defaults={'name': 'Information Science'})
    print("    [ok] Departments")

    # --- COURSES ---
    courses_data = [
        # CSE
        dict(code='CSE601', name='Machine Learning',
             department=cse, category='PROFESSIONAL', capacity=25, current_seats=0,
             job_perspective='ML Engineers are among the highest-paid in tech. Roles in AI startups, FAANG, and research labs.',
             salient_features='Supervised/Unsupervised learning, Neural Networks, Scikit-Learn, Python projects.',
             prerequisites='Linear Algebra, Python', is_open_elective=False),

        dict(code='CSE602', name='Cloud Computing & DevOps',
             department=cse, category='PROFESSIONAL', capacity=30, current_seats=0,
             job_perspective='Cloud architects earn Rs. 15-40 LPA. AWS, Azure, and GCP are industry standards.',
             salient_features='AWS services, Docker, Kubernetes, CI/CD pipelines, Terraform.',
             prerequisites='Networking Basics', is_open_elective=False),

        dict(code='CSE603', name='Blockchain Technology',
             department=cse, category='OPEN', capacity=20, current_seats=0,
             job_perspective='Blockchain developers are in high demand for FinTech, Supply Chain, and Web3 startups.',
             salient_features='Ethereum, Smart Contracts, Solidity, DeFi fundamentals.',
             prerequisites='Data Structures', is_open_elective=True),

        dict(code='CSE604', name='Natural Language Processing',
             department=cse, category='PROFESSIONAL', capacity=20, current_seats=0,
             job_perspective='NLP powers chatbots, search, and translation. Roles at OpenAI, Google, Microsoft.',
             salient_features='BERT, Transformers, Sentiment Analysis, Text Classification, HuggingFace.',
             prerequisites='Machine Learning Basics', is_open_elective=False),

        dict(code='CSE605', name='Cybersecurity & Ethical Hacking',
             department=cse, category='PROFESSIONAL', capacity=25, current_seats=0,
             job_perspective='Security analysts are critical in every org. CEH, OSCP certifications open global doors.',
             salient_features='Penetration testing, Kali Linux, Network security, OWASP Top 10.',
             prerequisites='Networking', is_open_elective=False),

        dict(code='CSE606', name='Data Science & Analytics',
             department=cse, category='PROFESSIONAL', capacity=30, current_seats=0,
             job_perspective='Data Scientists drive decisions at every top company. Average salary Rs. 12-25 LPA.',
             salient_features='Pandas, NumPy, Matplotlib, Power BI, SQL, Tableau, EDA.',
             prerequisites='Statistics, Python', is_open_elective=False),

        # ECE
        dict(code='ECE501', name='Internet of Things (IoT)',
             department=ece, category='OPEN', capacity=25, current_seats=0,
             job_perspective='IoT is the backbone of Smart Cities. Bosch, Honeywell, and startups hire IoT engineers.',
             salient_features='Arduino, Raspberry Pi, MQTT, Cloud IoT, sensor networks.',
             prerequisites='Basic Electronics', is_open_elective=True),

        dict(code='ECE502', name='VLSI Design',
             department=ece, category='PROFESSIONAL', capacity=20, current_seats=0,
             job_perspective='VLSI engineers at Intel, Qualcomm, and TSMC are in huge demand post chip-shortage era.',
             salient_features='Cadence, Verilog, CMOS design, chip fabrication flow.',
             prerequisites='Digital Electronics', is_open_elective=False),

        dict(code='ECE503', name='Embedded Systems',
             department=ece, category='PROFESSIONAL', capacity=25, current_seats=0,
             job_perspective='Automotive, aerospace, and consumer electronics all run on embedded systems.',
             salient_features='ARM Cortex, FreeRTOS, bare-metal programming, device drivers.',
             prerequisites='Microprocessors', is_open_elective=False),

        dict(code='ECE504', name='5G & Wireless Communications',
             department=ece, category='PROFESSIONAL', capacity=20, current_seats=0,
             job_perspective='5G rollout creates massive demand for RF and telecom engineers worldwide.',
             salient_features='OFDM, MIMO, beamforming, 5G NR standards, network slicing.',
             prerequisites='Communication Systems', is_open_elective=False),

        # ME
        dict(code='ME501', name='Robotics & Automation',
             department=me, category='PROFESSIONAL', capacity=20, current_seats=0,
             job_perspective='Industry 4.0 demands robotics engineers. Amazon, Tesla, and automotive giants hire heavily.',
             salient_features='ROS, kinematics, path planning, PLC programming, cobots.',
             prerequisites='Control Systems', is_open_elective=False),

        dict(code='ME502', name='Finite Element Analysis',
             department=me, category='PROFESSIONAL', capacity=20, current_seats=0,
             job_perspective='FEA is used in aerospace, automotive, and civil sectors for structural simulations.',
             salient_features='ANSYS, SolidWorks Simulation, mesh generation, stress analysis.',
             prerequisites='Engineering Mechanics', is_open_elective=False),

        dict(code='ME503', name='Automobile Engineering',
             department=me, category='OPEN', capacity=25, current_seats=0,
             job_perspective='EV revolution is creating roles in battery management, NVH, and powertrain design.',
             salient_features='IC engines, EV drivetrains, suspension systems, NVH analysis.',
             prerequisites='Thermodynamics', is_open_elective=True),

        # Open / Cross-disciplinary
        dict(code='OPEN701', name='Entrepreneurship & Startup Ecosystem',
             department=mba, category='ABILITY', capacity=40, current_seats=0,
             job_perspective='Ideal for students wanting to build startups. Learn pitch, funding, and product-market fit.',
             salient_features='Lean startup, MVP, VC pitch, case studies of Flipkart, Ola, Razorpay.',
             prerequisites='None', is_open_elective=True),

        dict(code='OPEN702', name='Design Thinking & Innovation',
             department=cse, category='ABILITY', capacity=35, current_seats=0,
             job_perspective='Product Managers and UX Designers use design thinking as their core methodology.',
             salient_features='Empathy mapping, ideation, prototyping, usability testing, Figma.',
             prerequisites='None', is_open_elective=True),

        dict(code='IS601', name='Full Stack Web Development',
             department=is_, category='OPEN', capacity=30, current_seats=0,
             job_perspective='Full stack roles dominate job boards. React + Node + Django skills command Rs. 10-20 LPA.',
             salient_features='React.js, Node.js, Django REST, PostgreSQL, deployment on Render/Vercel.',
             prerequisites='HTML/CSS basics', is_open_elective=True),
    ]

    for c in courses_data:
        Course.objects.get_or_create(code=c['code'], defaults=c)
    print("    [ok] %d Courses" % len(courses_data))

    # --- ADMIN USER ---
    admin_user, created = User.objects.get_or_create(username='admin')
    admin_user.set_password('admin123')
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    print("    [ok] Admin user  (admin / admin123)")

    # --- STUDENTS ---
    students_data = [
        dict(username='student1', password='pass123', full_name='Roshan Kumar',   usn='1RN21CS001', dept=cse,  cgpa=9.1, semester=6),
        dict(username='student2', password='pass123', full_name='Priya Sharma',   usn='1RN21CS002', dept=cse,  cgpa=8.4, semester=6),
        dict(username='student3', password='pass123', full_name='Arjun Mehta',    usn='1RN21CS003', dept=cse,  cgpa=7.8, semester=6),
        dict(username='student4', password='pass123', full_name='Sneha Patil',    usn='1RN21ECE01', dept=ece,  cgpa=8.9, semester=6),
        dict(username='student5', password='pass123', full_name='Rahul Nair',     usn='1RN21ECE02', dept=ece,  cgpa=7.2, semester=6),
        dict(username='student6', password='pass123', full_name='Divya Rao',      usn='1RN21ME001', dept=me,   cgpa=8.0, semester=6),
        dict(username='student7', password='pass123', full_name='Kiran Joshi',    usn='1RN21CS004', dept=cse,  cgpa=6.5, semester=6),
        dict(username='student8', password='pass123', full_name='Asha Reddy',     usn='1RN21IS001', dept=is_,  cgpa=8.7, semester=6),
    ]

    created_students = []
    for sd in students_data:
        user, _ = User.objects.get_or_create(username=sd['username'])
        user.set_password(sd['password'])
        user.first_name = sd['full_name'].split()[0]
        user.save()

        student, _ = Student.objects.get_or_create(user=user, defaults={
            'department': sd['dept'], 'cgpa': sd['cgpa'],
            'semester':   sd['semester'], 'full_name': sd['full_name'],
            'usn':        sd['usn'],
        })
        student.department = sd['dept']
        student.cgpa       = sd['cgpa']
        student.semester   = sd['semester']
        student.full_name  = sd['full_name']
        student.usn        = sd['usn']
        student.save()
        created_students.append(student)

    print("    [ok] %d Students" % len(created_students))

    # --- PREFERENCES ---
    ml     = Course.objects.get(code='CSE601')
    cloud  = Course.objects.get(code='CSE602')
    bc     = Course.objects.get(code='CSE603')
    nlp    = Course.objects.get(code='CSE604')
    cyber  = Course.objects.get(code='CSE605')
    ds     = Course.objects.get(code='CSE606')
    iot    = Course.objects.get(code='ECE501')
    vlsi   = Course.objects.get(code='ECE502')
    emb    = Course.objects.get(code='ECE503')
    robot  = Course.objects.get(code='ME501')
    web    = Course.objects.get(code='IS601')
    design = Course.objects.get(code='OPEN702')

    prefs_data = [
        (created_students[0], [(ml, 1),    (nlp, 2),   (ds, 3)]),      # 9.1 CGPA
        (created_students[1], [(ml, 1),    (cloud, 2), (cyber, 3)]),   # 8.4 CGPA
        (created_students[2], [(cloud, 1), (bc, 2),    (design, 3)]),  # 7.8 CGPA
        (created_students[3], [(iot, 1),   (vlsi, 2),  (emb, 3)]),     # 8.9 CGPA
        (created_students[4], [(iot, 1),   (emb, 2),   (design, 3)]),  # 7.2 CGPA
        (created_students[5], [(robot, 1), (iot, 2),   (design, 3)]),  # 8.0 CGPA
        (created_students[6], [(web, 1),   (design, 2),(bc, 3)]),      # 6.5 CGPA
        (created_students[7], [(web, 1),   (ml, 2),    (ds, 3)]),      # 8.7 CGPA
    ]

    for student, choices in prefs_data:
        student.preferences.all().delete()
        for course, rank in choices:
            Preference.objects.create(student=student, course=course, rank=rank)

    print("    [ok] Preferences for %d students" % len(prefs_data))

    # --- COURSE HISTORY ---
    history = [
        (created_students[0], 'CS101', 'Introduction to Programming'),
        (created_students[0], 'MA101', 'Engineering Mathematics'),
        (created_students[1], 'CS101', 'Introduction to Programming'),
        (created_students[3], 'EC101', 'Basic Electronics'),
    ]
    for student, code, name in history:
        StudentCourseHistory.objects.get_or_create(
            student=student, course_code=code,
            defaults={'course_name': name}
        )
    print("    [ok] Course history")

    print("")
    print("[DONE] Seeding complete!")
    print("=" * 48)
    print("  Admin login    :  admin / admin123")
    print("  Student login  :  student1 to student8 / pass123")
    print("=" * 48)


if __name__ == '__main__':
    populate()
