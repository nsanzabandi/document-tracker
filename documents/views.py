import datetime
from django.utils.dateparse import parse_date
from django.shortcuts import render, get_object_or_404, redirect
from .models import Document
from .forms import DocumentForm

from django.http import HttpResponse
import openpyxl
from django.db.models import Q, Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

@login_required
def document_list(request):
    status_filter = request.GET.get('status')
    division_filter = request.GET.get('division')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    documents = Document.objects.all().order_by('-created_at')

    # Keyword search
    query = request.GET.get('q')
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(receiver__icontains=query) |
            Q(notes__icontains=query)
        )

    if status_filter:
        documents = documents.filter(status=status_filter)
    if division_filter:
        documents = documents.filter(division=division_filter)
    if start_date:
        documents = documents.filter(doc_date__gte=parse_date(start_date))
    if end_date:
        documents = documents.filter(doc_date__lte=parse_date(end_date))

    # Compute priority for each document
    for doc in documents:
        doc.priority = doc.get_priority()

    # ✅ Custom sort based on priority level
    priority_order = {'High': 0, 'Moderate': 1, 'Low': 2, 'Treated': 3}
    sorted_documents = sorted(documents, key=lambda d: priority_order.get(d.priority, 4))

    # Stats
    total_docs = len(sorted_documents)
    pending_docs = sum(1 for d in sorted_documents if d.status == 'Pending')
    followed_docs = sum(1 for d in sorted_documents if d.status == 'Followed Up')
    resolved_docs = sum(1 for d in sorted_documents if d.status == 'Resolved')
    overdue_docs = sum(1 for d in sorted_documents if d.is_overdue())

    divisions = Document.objects.values_list('division', flat=True).distinct()

    priority_counts = {
        "High": sum(1 for d in sorted_documents if d.priority == "High"),
        "Moderate": sum(1 for d in sorted_documents if d.priority == "Moderate"),
        "Low": sum(1 for d in sorted_documents if d.priority == "Low"),
    }

    division_counts = documents.values('division').annotate(count=Count('id')).order_by('division')

    # ✅ Pagination
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
        'priority_counts': priority_counts,
        'division_counts': division_counts,
    }
    return render(request, 'documents/document_list.html', context)


@login_required
def export_documents_excel(request):
    documents = Document.objects.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Documents"

    headers = ['Title', 'Document Date', 'Follow-Up Date', 'Receiver', 'Division', 'Status', 'Notes']
    ws.append(headers)

    for doc in documents:
        ws.append([
            doc.title, doc.doc_date, doc.follow_up,
            doc.receiver, doc.division, doc.status, doc.notes
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
        form.save()
        return redirect('document_list')
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Add Document'})

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk)

    # Handle quick status update from list view
    if request.method == 'POST' and 'quick_status' in request.POST:
        new_status = request.POST.get('status')
        if new_status in ['Pending', 'Followed Up', 'Resolved']:
            doc.status = new_status
            doc.save()
        return redirect('document_list')

    # Handle normal edit form
    form = DocumentForm(request.POST or None, instance=doc)
    if form.is_valid():
        form.save()
        return redirect('document_list')
    return render(request, 'documents/document_form.html', {'form': form, 'title': 'Edit Document'})

@login_required
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk)
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
