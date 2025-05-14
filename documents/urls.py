from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('login/', views.simple_login, name='login'),
    path('logout/', views.simple_logout, name='logout'),
    path('add/', views.document_create, name='document_create'),
    path('edit/<int:pk>/', views.document_edit, name='document_edit'),
    path('delete/<int:pk>/', views.document_delete, name='document_delete'),
    path('export/', views.export_documents_excel, name='document_export'),
]

