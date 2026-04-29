from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('',                  views.landing,             name='landing'),
    path('catalog/',          views.catalog,             name='catalog'),

    # Auth
    path('login/',            views.student_login,       name='login'),
    path('logout/',           views.student_logout,      name='logout'),

    # Student
    path('dashboard/',        views.student_dashboard,   name='student_dashboard'),
    path('submit/',           views.submit_preference,   name='submit_preference'),
    path('results/',          views.my_results,          name='my_results'),
    path('recommendations/',  views.recommendations_view,name='recommendations'),

    # Admin
    path('admin-dashboard/',  views.admin_dashboard,     name='admin_dashboard'),
    path('export/',           views.export_csv,          name='export_csv'),

    # API
    path('api/seats/',               views.api_live_seats,     name='api_live_seats'),
    path('api/seats/<int:course_id>/',views.api_seat_single,   name='api_seat_single'),
    path('api/check-course/<int:course_id>/', views.check_and_suggest, name='check_and_suggest'),
]