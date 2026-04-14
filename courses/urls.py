from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),   # visiting / shows login
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('home/', views.index, name='index'),
    path('student/<str:student_id>', views.student_dashboard, name='dashboard'),
    path('catalog/', views.course_catalog, name='catalog'),
    path('prerequisites/', views.prerequisites, name='prerequisites'),
    path('plan/', views.plan_schedule, name='plan_schedule'),
    path('api/get-student/', views.get_student, name='get_student'),
    path('student/<str:student_id>/download-pdf/', views.download_schedule_pdf, name='download_pdf'),
    path('schedule/', views.schedule, name='schedule'),
    path('student/<str:student_id>/delete-course/<int:course_id>/', views.delete_completed_course, name='delete_course'),
]