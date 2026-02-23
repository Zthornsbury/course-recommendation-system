from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('student/<str:student_id>', views.student_dashboard, name='dashboard'),
    path('catalog/', views.course_catalog, name='catalog'),
    path('prerequisites/', views.prerequisites, name='prerequisites'),
    path('plan/', views.plan_schedule, name='plan_schedule'),
    path('api/get-student/', views.get_student, name='get_student'),
    path('student/<str:student_id>/download-pdf/', views.download_schedule_pdf, name='download_pdf'),

]