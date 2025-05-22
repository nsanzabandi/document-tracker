import datetime
from django.utils.dateparse import parse_date
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q, Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
import openpyxl
from django.db.models import F
from .models import Division
from .models import Document, Profile
from .forms import DocumentForm, AdminUserCreateForm

from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required



@login_required
def document_list(request):
    status_filter = request.GET.get('status')
    division_filter = request.GET.get('division')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # 🔐 Filter based on user role
    if request.user.is_superuser:
        documents = Document.objects.all().order_by('-created_at')
    else:
        # Show user's own documents + documents where they are the receiver
        documents_query = Q(created_by=request.user)  # Documents they created
        
        # Check if user is linked to a staff member
        try:
            staff_member = request.user.staff_profile
            documents_query |= Q(receiver=staff_member)  # Documents assigned to their staff profile
        except:
            # Fallback: match by name if no staff link exists
            user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            if user_full_name:
                documents_query |= Q(receiver__name__icontains=user_full_name)
        
        documents = Document.objects.filter(documents_query).order_by('-created_at')

    query = request.GET.get('q')
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(receiver__name__icontains=query) |
            Q(purpose__icontains=query)
        )

    if status_filter:
        documents = documents.filter(status=status_filter)
    if division_filter:
        documents = documents.filter(division=division_filter)
    if start_date:
        documents = documents.filter(doc_date__gte=parse_date(start_date))
    if end_date:
        documents = documents.filter(doc_date__lte=parse_date(end_date))

    # Add metadata for each document
    for doc in documents:
        doc.priority = doc.get_priority()
        # Check if current user can edit/delete this document
        doc.can_edit = (request.user.is_superuser or doc.created_by == request.user)
        doc.can_delete = (request.user.is_superuser or doc.created_by == request.user)
        doc.can_change_status = True  # All users can change status of documents they have access to

    priority_order = {'High': 0, 'Moderate': 1, 'Low': 2, 'Treated': 3}
    sorted_documents = sorted(documents, key=lambda d: priority_order.get(d.priority, 4))

    total_docs = len(sorted_documents)
    pending_docs = sum(1 for d in sorted_documents if d.status == 'Pending')
    followed_docs = sum(1 for d in sorted_documents if d.status == 'Followed Up')
    resolved_docs = sum(1 for d in sorted_documents if d.status == 'Resolved')
    overdue_docs = sum(1 for d in sorted_documents if d.is_overdue())

    division_ids = Document.objects.values_list('division', flat=True).distinct()
    divisions = Division.objects.filter(id__in=division_ids)
    status_counts = {
        "Pending": pending_docs,
        "Followed_Up": followed_docs,
        "Resolved": resolved_docs,
        "Overdue": overdue_docs,
    }
    division_counts = (
        documents
        .values('division__name')
        .annotate(count=Count('id'))
        .order_by('division__name')
    )

    paginator = Paginator(sorted_documents, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'documents': page_obj,
        'total_docs': total_docs,
        'pending_docs': pending_docs,
        'followed_docs': followed_docs,
        'resolved_docs': resolved_docs,
        'overdue_docs': overdue_docs,
        'divisions': divisions,
        'page_obj': page_obj,
        'query': request.GET.get('q', ''),
        'status_counts': status_counts,
        'division_counts': division_counts,
    }
    return render(request, 'documents/document_list.html', context)



@login_required
def export_documents_excel(request):
    if request.user.is_superuser:
        documents = Document.objects.all()
    else:
        documents = Document.objects.filter(created_by=request.user)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Documents Recorded Report"
    headers = ['Title', 'Purpose', 'Document Date', 'Follow-Up Date', 'Receiver', 'Division', 'Status']
    ws.append(headers)

    for doc in documents:
        ws.append([
            doc.title,
            doc.purpose,
            doc.doc_date,
            doc.follow_up,
            str(doc.receiver),
            str(doc.division),
            doc.status
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=documents.xlsx'
    wb.save(response)
    return response



@login_required
def document_create(request):
    form = DocumentForm(request.POST or None)
    if form.is_valid():
        doc = form.save(commit=False)
        doc.status = 'Pending'
        doc.created_by = request.user
        doc.save()
        return redirect('document_list')
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Add Document'})


@login_required
def document_edit(request, pk):
    # Get document based on permissions
    if request.user.is_superuser:
        doc = get_object_or_404(Document, pk=pk)
    else:
        # User can edit if they created it OR if they are the receiver
        documents_query = Q(pk=pk) & Q(created_by=request.user)  # Documents they created
        
        # Check if user is linked to a staff member
        try:
            staff_member = request.user.staff_profile
            documents_query |= Q(pk=pk) & Q(receiver=staff_member)
        except:
            # Fallback: match by name if no staff link exists
            user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            if user_full_name:
                documents_query |= Q(pk=pk) & Q(receiver__name__icontains=user_full_name)
        
        doc = get_object_or_404(Document, documents_query)

    # Check if user is only the receiver (not creator)
    is_receiver_only = False
    if doc.created_by != request.user and not request.user.is_superuser:
        try:
            # Check if user is the receiver via staff link
            is_receiver_only = (hasattr(request.user, 'staff_profile') and 
                              doc.receiver == request.user.staff_profile)
        except:
            # Fallback: check by name
            user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            is_receiver_only = user_full_name in doc.receiver.name

    # Handle quick status update (for receivers)
    if request.method == 'POST' and 'quick_status' in request.POST:
        new_status = request.POST.get('status')
        if new_status in ['Pending', 'Followed Up', 'Resolved']:
            doc.status = new_status
            doc.save()
        return redirect('document_list')

    # Handle full form submission
    if request.method == 'POST' and not is_receiver_only:
        form = DocumentForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            return redirect('document_list')
    else:
        form = DocumentForm(instance=doc)

    context = {
        'form': form, 
        'title': 'Edit Document',
        'document': doc,
        'is_receiver_only': is_receiver_only,
    }
    return render(request, 'documents/document_form.html', context)

@login_required
def document_delete(request, pk):
    # Only allow deletion if user created the document or is superuser
    doc = get_object_or_404(Document, pk=pk, created_by=request.user)
    
    if not (request.user.is_superuser or doc.created_by == request.user):
        # Redirect with error message or show permission denied
        return redirect('document_list')

    if request.method == 'POST':
        doc.delete()
        return redirect('document_list')
    return render(request, 'documents/document_confirm_delete.html', {'document': doc})


def simple_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('document_list')
        else:
            return render(request, 'documents/login.html', {'error': 'Invalid credentials'})
    return render(request, 'documents/login.html')


def simple_logout(request):
    logout(request)
    return redirect('login')


@staff_member_required
def admin_create_user(request):
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, division=form.cleaned_data['division'])
            return redirect('document_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'documents/register.html', {'form': form, 'title': 'Create New User'})



def is_admin(user):
    return user.is_superuser or user.is_staff

@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().select_related('profile')
    return render(request, 'documents/user_list.html', {'users': users})


@user_passes_test(is_admin)
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            user.profile.division = form.cleaned_data['division']
            user.profile.save()
            return redirect('user_list')
    else:
        initial_data = {'division': user.profile.division}
        form = AdminUserCreateForm(instance=user, initial=initial_data)
    return render(request, 'documents/register.html', {'form': form, 'title': f'Edit User - {user.username}'})


@user_passes_test(is_admin)
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('user_list')
    return render(request, 'documents/user_confirm_delete.html', {'user': user})



@staff_member_required
@require_POST
def update_user_role(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    role = request.POST.get('role')
    if role == 'admin':
        user.is_superuser = True
        user.is_staff = True
    else:
        user.is_superuser = False
        user.is_staff = False
    user.save()
    return redirect('user_list')


@login_required
def document_change_status(request, pk):
    if request.method == 'POST':
        # Get document if user has access to it
        if request.user.is_superuser:
            doc = get_object_or_404(Document, pk=pk)
        else:
            documents_query = Q(created_by=request.user)  # Documents they created
            
            # Check if user is linked to a staff member
            try:
                staff_member = request.user.staff_profile
                documents_query |= Q(receiver=staff_member)
            except:
                # Fallback: match by name if no staff link exists
                user_full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                if user_full_name:
                    documents_query |= Q(receiver__name__icontains=user_full_name)
            
            doc = get_object_or_404(Document, Q(pk=pk) & documents_query)
        
        new_status = request.POST.get('status')
        if new_status in ['Pending', 'Followed Up', 'Resolved']:
            doc.status = new_status
            doc.save()
    
    return redirect('document_list')