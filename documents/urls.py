# documents/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('create-user/', views.admin_create_user, name='admin_create_user'),
    path('login/', views.simple_login, name='login'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('logout/', views.simple_logout, name='logout'),
    path('add/', views.document_create, name='document_create'),
    path('edit/<int:pk>/', views.document_edit, name='document_edit'),
    path('delete/<int:pk>/', views.document_delete, name='document_delete'),
    path('export/', views.export_documents_excel, name='document_export'),

    path('users/<int:user_id>/role/', views.update_user_role, name='update_user_role'),

    # ✅ Your custom password reset flow
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
]