from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('student/<str:student_id>', views.student_dashboard, name='dashboard'),
    path('api/student/', views.get_student, name='student'),
]