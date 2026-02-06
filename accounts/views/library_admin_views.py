import csv
from datetime import date
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from weasyprint import HTML
from library.models import BookCategory, Book, BookBorrow, BookCopy, BookReturn, BorrowingRules
from accounts.models import Staffs
from students.models import Student
from django.db.models import Avg
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect
from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum
from weasyprint.text.fonts import FontConfiguration
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import F

@login_required
def book_categories_list(request):
    """Display book categories management page"""
    categories = BookCategory.objects.all().order_by('name')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'admin/library/book_categories_list.html', context)


@login_required
def book_categories_crud(request):
    """Handle AJAX CRUD operations for book categories"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_book_category(request)
            elif action == 'update':
                return update_book_category(request)
            elif action == 'delete':
                return delete_book_category(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_book_category(request):
    """Create a new book category"""
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Category name is required.'
        })
    
    code = request.POST.get('code', '').strip().upper()
    if not code:
        return JsonResponse({
            'success': False,
            'message': 'Category code is required.'
        })
    
    # Validate name and code length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Category name must be at least 2 characters long.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Category name cannot exceed 100 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Category code cannot exceed 20 characters.'
        })
    
    # Validate code format (uppercase letters and numbers only)
    if not code.isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Category code can only contain letters and numbers.'
        })
    
    # Check for duplicate category name
    if BookCategory.objects.filter(name__iexact=name).exists():
        return JsonResponse({
            'success': False,
            'message': f'Category with name "{name}" already exists.'
        })
    
    # Check for duplicate category code
    if BookCategory.objects.filter(code__iexact=code).exists():
        return JsonResponse({
            'success': False,
            'message': f'Category with code "{code}" already exists.'
        })
    
    # Get optional fields
    description = request.POST.get('description', '').strip()
    
    try:
        # Create the book category
        category = BookCategory.objects.create(
            name=name,
            code=code,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{name}" created successfully.',
            'category': {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'description': category.description,
                'created_at': category.created_at.strftime('%b %d, %Y'),
                'updated_at': category.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'name' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'A category with name "{name}" already exists.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'A category with code "{code}" already exists.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating category: {str(e)}'
        })


def update_book_category(request):
    """Update an existing book category"""
    category_id = request.POST.get('id')
    if not category_id:
        return JsonResponse({
            'success': False,
            'message': 'Category ID is required.'
        })
    
    try:
        category = BookCategory.objects.get(id=category_id)
    except BookCategory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Category not found.'
        })
    
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    
    if not name or not code:
        return JsonResponse({
            'success': False,
            'message': 'Name and code are required.'
        })
    
    # Validate name and code length
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Category name must be at least 2 characters long.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Category name cannot exceed 100 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Category code cannot exceed 20 characters.'
        })
    
    # Validate code format (uppercase letters and numbers only)
    if not code.isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Category code can only contain letters and numbers.'
        })
    
    # Check for duplicate category name (excluding current)
    if BookCategory.objects.filter(name__iexact=name).exclude(id=category.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Category with name "{name}" already exists.'
        })
    
    # Check for duplicate category code (excluding current)
    if BookCategory.objects.filter(code__iexact=code).exclude(id=category.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Category with code "{code}" already exists.'
        })
    
    # Get optional fields
    description = request.POST.get('description', '').strip()
    
    try:
        # Update the book category
        category.name = name
        category.code = code
        category.description = description
        category.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{name}" updated successfully.',
            'category': {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'description': category.description,
                'updated_at': category.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'name' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'A category with name "{name}" already exists.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'A category with code "{code}" already exists.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating category: {str(e)}'
        })


def delete_book_category(request):
    """Delete a book category"""
    category_id = request.POST.get('id')
    if not category_id:
        return JsonResponse({
            'success': False,
            'message': 'Category ID is required.'
        })
    
    try:
        category = BookCategory.objects.get(id=category_id)
    except BookCategory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Category not found.'
        })
    
    category_name = category.name
    
    try:
        # Check if category has associated books
        # Uncomment if you have a Book model with ForeignKey to BookCategory
        # if category.book_set.exists():
        #     return JsonResponse({
        #         'success': False,
        #         'message': f'Cannot delete category "{category_name}" because it has associated books.'
        #     })
        
        category.delete()
        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" deleted successfully.',
            'id': category_id
        })
    except ProtectedError:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete category "{category_name}" because it has associated books.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting category: {str(e)}'
        })




@login_required
def books_list(request):
    """Display books management page"""
    books = Book.objects.select_related('category').all().order_by('title', 'author')
    categories = BookCategory.objects.all().order_by('name')
    

    book_type_choices = Book.BOOK_TYPE_CHOICES
    condition_choices = Book._meta.get_field('condition').choices
    status_choices = Book.BOOK_STATUS_CHOICES
    
    # Count statistics
    available_books_count = books.filter(status='available').count()
    borrowed_books_count = books.filter(status='borrowed').count()
    
    context = {
        'books': books,
        'categories': categories,
        'book_type_choices': book_type_choices,
        'condition_choices': condition_choices,
        'status_choices': status_choices,
        'available_books_count': available_books_count,
        'borrowed_books_count': borrowed_books_count,
    }
    
    return render(request, 'admin/library/books_list.html', context)


@login_required
def books_crud(request):
    """Handle AJAX CRUD operations for books"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_book(request)
            elif action == 'update':
                return update_book(request)
            elif action == 'toggle_status':
                return toggle_book_status(request)
            elif action == 'toggle_reference':
                return toggle_book_reference(request)
            elif action == 'delete':
                return delete_book(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_book(request):
    """Create a new book"""
    # Get and validate required fields
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({
            'success': False,
            'message': 'Book title is required.'
        })
    
    author = request.POST.get('author', '').strip()
    if not author:
        return JsonResponse({
            'success': False,
            'message': 'Author is required.'
        })
    
    category_id = request.POST.get('category')
    if not category_id:
        return JsonResponse({
            'success': False,
            'message': 'Category is required.'
        })
    
    book_type = request.POST.get('book_type')
    if not book_type:
        return JsonResponse({
            'success': False,
            'message': 'Book type is required.'
        })
    
    condition = request.POST.get('condition')
    if not condition:
        return JsonResponse({
            'success': False,
            'message': 'Condition is required.'
        })
    
    status = request.POST.get('status')
    if not status:
        return JsonResponse({
            'success': False,
            'message': 'Status is required.'
        })
    
    language = request.POST.get('language', '').strip()
    if not language:
        return JsonResponse({
            'success': False,
            'message': 'Language is required.'
        })
    
    fine_amount = request.POST.get('fine_amount', '500')
    total_copies = request.POST.get('total_copies', '1')
    
    # Validate title and author length
    if len(title) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Book title must be at least 2 characters long.'
        })
    
    if len(title) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Book title cannot exceed 200 characters.'
        })
    
    if len(author) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Author name must be at least 2 characters long.'
        })
    
    if len(author) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Author name cannot exceed 200 characters.'
        })
    
    # Validate fine amount
    try:
        fine_amount = float(fine_amount)
        if fine_amount < 0:
            return JsonResponse({
                'success': False,
                'message': 'Fine amount cannot be negative.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid fine amount.'
        })
    
    # Validate total copies
    try:
        total_copies = int(total_copies)
        if total_copies < 1:
            return JsonResponse({
                'success': False,
                'message': 'Total copies must be at least 1.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid total copies value.'
        })
    
    # Get category
    try:
        category = BookCategory.objects.get(id=category_id)
    except BookCategory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected category does not exist.'
        })
    
    # Check for duplicate ISBN if provided
    isbn = request.POST.get('isbn', '').strip()
    if isbn:
        if Book.objects.filter(isbn__iexact=isbn).exists():
            return JsonResponse({
                'success': False,
                'message': f'Book with ISBN "{isbn}" already exists.'
            })
    
    # Get optional fields
    publisher = request.POST.get('publisher', '').strip()
    publication_year = request.POST.get('publication_year', '').strip()
    edition = request.POST.get('edition', '').strip()
    location_code = request.POST.get('location_code', '').strip()
    pages = request.POST.get('pages', '').strip()
    description = request.POST.get('description', '').strip()
    keywords = request.POST.get('keywords', '').strip()
    
    # Publication year validation
    if publication_year:
        try:
            publication_year = int(publication_year)
            from datetime import datetime
            current_year = datetime.now().year
            if publication_year > current_year:
                return JsonResponse({
                    'success': False,
                    'message': 'Publication year cannot be in the future.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid publication year.'
            })
    else:
        publication_year = None
    
    # Pages validation
    if pages:
        try:
            pages = int(pages)
            if pages < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Pages must be at least 1.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid pages value.'
            })
    else:
        pages = None
    
    # Get borrowed copies
    borrowed_copies = request.POST.get('borrowed_copies', '0')
    try:
        borrowed_copies = int(borrowed_copies)
        if borrowed_copies < 0:
            borrowed_copies = 0
        if borrowed_copies > total_copies:
            return JsonResponse({
                'success': False,
                'message': 'Borrowed copies cannot exceed total copies.'
            })
    except ValueError:
        borrowed_copies = 0
    
    # Calculate available copies
    available_copies = total_copies - borrowed_copies
    
    # Get boolean fields
    is_reference = request.POST.get('is_reference') == 'on' or request.POST.get('is_reference') == 'true'
    
    try:
        # Create the book (accession number and barcode will be auto-generated in save() method)
        book = Book.objects.create(
            title=title,
            author=author,
            isbn=isbn if isbn else None,
            publisher=publisher,
            publication_year=publication_year,
            edition=edition,
            category=category,
            book_type=book_type,
            location_code=location_code,
            pages=pages,
            language=language,
            description=description,
            keywords=keywords,
            condition=condition,
            status=status,
            is_reference=is_reference,
            fine_amount=fine_amount,
            total_copies=total_copies,
            borrowed_copies=borrowed_copies,
            available_copies=available_copies
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Book "{title}" created successfully.',
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'isbn': book.isbn,
                'publisher': book.publisher,
                'publication_year': book.publication_year,
                'edition': book.edition,
                'category_id': book.category.id if book.category else None,
                'category_name': book.category.name if book.category else None,
                'book_type': book.book_type,
                'book_type_display': book.get_book_type_display(),
                'accession_number': book.accession_number,
                'barcode': book.barcode,
                'location_code': book.location_code,
                'pages': book.pages,
                'language': book.language,
                'description': book.description,
                'keywords': book.keywords,
                'condition': book.condition,
                'condition_display': book.get_condition_display(),
                'status': book.status,
                'status_display': book.get_status_display(),
                'is_reference': book.is_reference,
                'fine_amount': float(book.fine_amount),
                'total_copies': book.total_copies,
                'borrowed_copies': book.borrowed_copies,
                'available_copies': book.available_copies
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'isbn' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'A book with ISBN "{isbn}" already exists.'
                })
            elif 'accession_number' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': 'Generated accession number already exists. Please try again.'
                })
            elif 'barcode' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': 'Generated barcode already exists. Please try again.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating book: {str(e)}'
        })


def update_book(request):
    """Update an existing book"""
    book_id = request.POST.get('id')
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book ID is required.'
        })
    
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })
    
    # Get and validate required fields
    title = request.POST.get('title', '').strip()
    author = request.POST.get('author', '').strip()
    category_id = request.POST.get('category')
    book_type = request.POST.get('book_type')
    condition = request.POST.get('condition')
    status = request.POST.get('status')
    language = request.POST.get('language', '').strip()
    fine_amount = request.POST.get('fine_amount')
    total_copies = request.POST.get('total_copies')
    
    if not title or not author or not category_id or not book_type or not condition or not status or not language:
        return JsonResponse({
            'success': False,
            'message': 'All required fields must be filled.'
        })
    
    # Validate title and author length
    if len(title) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Book title must be at least 2 characters long.'
        })
    
    if len(title) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Book title cannot exceed 200 characters.'
        })
    
    if len(author) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Author name must be at least 2 characters long.'
        })
    
    if len(author) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Author name cannot exceed 200 characters.'
        })
    
    # Validate fine amount
    try:
        fine_amount = float(fine_amount)
        if fine_amount < 0:
            return JsonResponse({
                'success': False,
                'message': 'Fine amount cannot be negative.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid fine amount.'
        })
    
    # Validate total copies
    try:
        total_copies = int(total_copies)
        if total_copies < 1:
            return JsonResponse({
                'success': False,
                'message': 'Total copies must be at least 1.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid total copies value.'
        })
    
    # Get category
    try:
        category = BookCategory.objects.get(id=category_id)
    except BookCategory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected category does not exist.'
        })
    
    # Check for duplicate ISBN if provided (excluding current book)
    isbn = request.POST.get('isbn', '').strip()
    if isbn:
        if Book.objects.filter(isbn__iexact=isbn).exclude(id=book.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'Another book with ISBN "{isbn}" already exists.'
            })
    else:
        isbn = None
    
    # Get optional fields
    publisher = request.POST.get('publisher', '').strip()
    publication_year = request.POST.get('publication_year', '').strip()
    edition = request.POST.get('edition', '').strip()
    location_code = request.POST.get('location_code', '').strip()
    pages = request.POST.get('pages', '').strip()
    description = request.POST.get('description', '').strip()
    keywords = request.POST.get('keywords', '').strip()
    
    # Publication year validation
    if publication_year:
        try:
            publication_year = int(publication_year)
            from datetime import datetime
            current_year = datetime.now().year
            if publication_year > current_year:
                return JsonResponse({
                    'success': False,
                    'message': 'Publication year cannot be in the future.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid publication year.'
            })
    else:
        publication_year = None
    
    # Pages validation
    if pages:
        try:
            pages = int(pages)
            if pages < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Pages must be at least 1.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid pages value.'
            })
    else:
        pages = None
    
    # Get borrowed copies
    borrowed_copies = request.POST.get('borrowed_copies', '0')
    try:
        borrowed_copies = int(borrowed_copies)
        if borrowed_copies < 0:
            borrowed_copies = 0
        if borrowed_copies > total_copies:
            return JsonResponse({
                'success': False,
                'message': 'Borrowed copies cannot exceed total copies.'
            })
    except ValueError:
        borrowed_copies = 0
    
    # Calculate available copies
    available_copies = total_copies - borrowed_copies
    
    # Get boolean fields
    is_reference = request.POST.get('is_reference') == 'on' or request.POST.get('is_reference') == 'true'
    
    try:
        # Update the book
        book.title = title
        book.author = author
        book.isbn = isbn
        book.publisher = publisher
        book.publication_year = publication_year
        book.edition = edition
        book.category = category
        book.book_type = book_type
        book.location_code = location_code
        book.pages = pages
        book.language = language
        book.description = description
        book.keywords = keywords
        book.condition = condition
        book.status = status
        book.is_reference = is_reference
        book.fine_amount = fine_amount
        book.total_copies = total_copies
        book.borrowed_copies = borrowed_copies
        book.available_copies = available_copies
        
        # Validate and save
        book.full_clean()
        book.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Book "{title}" updated successfully.',
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'isbn': book.isbn,
                'publisher': book.publisher,
                'publication_year': book.publication_year,
                'edition': book.edition,
                'category_id': book.category.id if book.category else None,
                'category_name': book.category.name if book.category else None,
                'book_type': book.book_type,
                'book_type_display': book.get_book_type_display(),
                'accession_number': book.accession_number,
                'barcode': book.barcode,
                'location_code': book.location_code,
                'pages': book.pages,
                'language': book.language,
                'description': book.description,
                'keywords': book.keywords,
                'condition': book.condition,
                'condition_display': book.get_condition_display(),
                'status': book.status,
                'status_display': book.get_status_display(),
                'is_reference': book.is_reference,
                'fine_amount': float(book.fine_amount),
                'total_copies': book.total_copies,
                'borrowed_copies': book.borrowed_copies,
                'available_copies': book.available_copies
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'isbn' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'Another book with ISBN "{isbn}" already exists.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating book: {str(e)}'
        })


def toggle_book_status(request):
    """Toggle book status between available and unavailable"""
    book_id = request.POST.get('id')
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book ID is required.'
        })
    
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })
    
    # Toggle status
    if book.status == 'available':
        book.status = 'unavailable'
        action = 'marked as unavailable'
    else:
        book.status = 'available'
        action = 'marked as available'
    
    try:
        book.save()
        return JsonResponse({
            'success': True,
            'message': f'Book "{book.title}" {action}.',
            'status': book.status,
            'status_display': book.get_status_display()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating book status: {str(e)}'
        })


def toggle_book_reference(request):
    """Toggle book reference status"""
    book_id = request.POST.get('id')
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book ID is required.'
        })
    
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })
    
    # Toggle reference status
    book.is_reference = not book.is_reference
    action = 'marked as reference' if book.is_reference else 'marked as non-reference'
    
    try:
        book.save()
        return JsonResponse({
            'success': True,
            'message': f'Book "{book.title}" {action}.',
            'is_reference': book.is_reference
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating book reference status: {str(e)}'
        })


def delete_book(request):
    """Delete a book"""
    book_id = request.POST.get('id')
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book ID is required.'
        })
    
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })
    

    active_borrows = BookBorrow.objects.filter(
        book=book,
        status__in=['active', 'overdue']
    ).exists()
    
    if active_borrows:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete book "{book.title}" because it has active borrows.'
        })
    
    book_title = book.title
    
    try:
        book.delete()
        return JsonResponse({
            'success': True,
            'message': f'Book "{book_title}" deleted successfully.',
            'id': book_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting book: {str(e)}'
        })


@login_required
def get_book_data(request, book_id):
    """Get book data for editing via AJAX"""
    try:
        book = Book.objects.get(id=book_id)
        return JsonResponse({
            'success': True,
            'book': {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'isbn': book.isbn,
                'publisher': book.publisher,
                'publication_year': book.publication_year,
                'edition': book.edition,
                'category': book.category.id if book.category else None,
                'book_type': book.book_type,
                'accession_number': book.accession_number,
                'barcode': book.barcode,
                'location_code': book.location_code,
                'pages': book.pages,
                'language': book.language,
                'description': book.description,
                'keywords': book.keywords,
                'condition': book.condition,
                'status': book.status,
                'is_reference': book.is_reference,
                'fine_amount': float(book.fine_amount),
                'total_copies': book.total_copies,
                'borrowed_copies': book.borrowed_copies,
                'available_copies': book.available_copies,
            }
        })
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })




@login_required
def book_copies_list(request, book_id=None):
    """Display book copies management page"""
    # Get book if book_id is provided
    book = None
    if book_id:
        book = get_object_or_404(Book, id=book_id)
        copies = BookCopy.objects.filter(book=book).order_by('copy_number')
    else:
        copies = BookCopy.objects.select_related('book').all().order_by('book__title', 'copy_number')
        book = None
    
    books = Book.objects.all().order_by('title')
    
    # Get choices for templates
    copy_status_choices = BookCopy.COPY_STATUS_CHOICES
    condition_choices = BookCopy._meta.get_field('condition').choices
    
    # Count statistics
    available_copies_count = copies.filter(status='available').count()
    borrowed_copies_count = copies.filter(status='borrowed').count()
    damaged_copies_count = copies.filter(status='damaged').count()
    
    context = {
        'copies': copies,
        'book': book,
        'books': books,
        'copy_status_choices': copy_status_choices,
        'condition_choices': condition_choices,
        'available_copies_count': available_copies_count,
        'borrowed_copies_count': borrowed_copies_count,
        'damaged_copies_count': damaged_copies_count,
    }
    
    return render(request, 'admin/library/book_copies_list.html', context)


@login_required
def book_copies_crud(request):
    """Handle AJAX CRUD operations for book copies"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_book_copy(request)
            elif action == 'update':
                return update_book_copy(request)
            elif action == 'toggle_status':
                return toggle_copy_status(request)
            elif action == 'delete':
                return delete_book_copy(request)
            elif action == 'bulk_create':
                return bulk_create_copies(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_book_copy(request):
    """Create a new book copy"""
    # Get and validate required fields
    book_id = request.POST.get('book')
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book selection is required.'
        })
    
    copy_number = request.POST.get('copy_number', '').strip()
    if not copy_number:
        return JsonResponse({
            'success': False,
            'message': 'Copy number is required.'
        })
    
    status = request.POST.get('status')
    if not status:
        return JsonResponse({
            'success': False,
            'message': 'Status is required.'
        })
    
    condition = request.POST.get('condition')
    if not condition:
        return JsonResponse({
            'success': False,
            'message': 'Condition is required.'
        })
    
    # Get book
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected book does not exist.'
        })
    
    # Validate copy number format
    try:
        # Ensure copy number is numeric and at least 3 digits
        copy_num = int(copy_number)
        copy_number = f"{copy_num:03d}"
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Copy number must be a number.'
        })
    
    # Check for duplicate copy number for this book
    if BookCopy.objects.filter(book=book, copy_number=copy_number).exists():
        return JsonResponse({
            'success': False,
            'message': f'Copy number "{copy_number}" already exists for this book.'
        })
    
    # Get optional fields
    barcode = request.POST.get('barcode', '').strip()
    accession_number = request.POST.get('accession_number', '').strip()
    notes = request.POST.get('notes', '').strip()
    purchase_date = request.POST.get('purchase_date', '').strip()
    purchase_price = request.POST.get('purchase_price', '').strip()
    
    # Validate purchase date if provided
    if purchase_date:
        try:
            purchase_date = date.fromisoformat(purchase_date)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid purchase date format. Use YYYY-MM-DD.'
            })
    else:
        purchase_date = None
    
    # Validate purchase price if provided
    if purchase_price:
        try:
            purchase_price = float(purchase_price)
            if purchase_price < 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Purchase price cannot be negative.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid purchase price.'
            })
    else:
        purchase_price = None
    
    try:
        # Create the book copy (barcode and accession number will be auto-generated if not provided)
        copy = BookCopy.objects.create(
            book=book,
            copy_number=copy_number,
            barcode=barcode if barcode else None,
            accession_number=accession_number if accession_number else None,
            status=status,
            condition=condition,
            notes=notes,
            purchase_date=purchase_date,
            purchase_price=purchase_price
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Copy {copy_number} of "{book.title}" created successfully.',
            'copy': {
                'id': copy.id,
                'book_id': copy.book.id,
                'book_title': copy.book.title,
                'copy_number': copy.copy_number,
                'barcode': copy.barcode,
                'accession_number': copy.accession_number,
                'status': copy.status,
                'status_display': copy.get_status_display(),
                'condition': copy.condition,
                'condition_display': copy.get_condition_display(),
                'notes': copy.notes,
                'purchase_date': copy.purchase_date.strftime('%b %d, %Y') if copy.purchase_date else '',
                'purchase_price': float(copy.purchase_price) if copy.purchase_price else None,
                'created_at': copy.created_at.strftime('%b %d, %Y'),
                'updated_at': copy.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'barcode' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'A copy with barcode "{barcode}" already exists.'
                })
            elif 'accession_number' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'A copy with accession number "{accession_number}" already exists.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating copy: {str(e)}'
        })


def update_book_copy(request):
    """Update an existing book copy"""
    copy_id = request.POST.get('id')
    if not copy_id:
        return JsonResponse({
            'success': False,
            'message': 'Copy ID is required.'
        })
    
    try:
        copy = BookCopy.objects.get(id=copy_id)
    except BookCopy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Copy not found.'
        })
    
    # Get and validate required fields
    copy_number = request.POST.get('copy_number', '').strip()
    status = request.POST.get('status')
    condition = request.POST.get('condition')
    
    if not copy_number or not status or not condition:
        return JsonResponse({
            'success': False,
            'message': 'Copy number, status, and condition are required.'
        })
    
    # Validate copy number format
    try:
        # Ensure copy number is numeric and at least 3 digits
        copy_num = int(copy_number)
        copy_number = f"{copy_num:03d}"
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Copy number must be a number.'
        })
    
    # Check for duplicate copy number for this book (excluding current)
    if BookCopy.objects.filter(book=copy.book, copy_number=copy_number).exclude(id=copy.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Copy number "{copy_number}" already exists for this book.'
        })
    
    # Get optional fields
    barcode = request.POST.get('barcode', '').strip()
    accession_number = request.POST.get('accession_number', '').strip()
    notes = request.POST.get('notes', '').strip()
    purchase_date = request.POST.get('purchase_date', '').strip()
    purchase_price = request.POST.get('purchase_price', '').strip()
    
    # Validate barcode uniqueness if changed
    if barcode and barcode != copy.barcode:
        if BookCopy.objects.filter(barcode=barcode).exclude(id=copy.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A copy with barcode "{barcode}" already exists.'
            })
    
    # Validate accession number uniqueness if changed
    if accession_number and accession_number != copy.accession_number:
        if BookCopy.objects.filter(accession_number=accession_number).exclude(id=copy.id).exists():
            return JsonResponse({
                'success': False,
                'message': f'A copy with accession number "{accession_number}" already exists.'
            })
    
    # Validate purchase date if provided
    if purchase_date:
        try:
            purchase_date = date.fromisoformat(purchase_date)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid purchase date format. Use YYYY-MM-DD.'
            })
    else:
        purchase_date = None
    
    # Validate purchase price if provided
    if purchase_price:
        try:
            purchase_price = float(purchase_price)
            if purchase_price < 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Purchase price cannot be negative.'
                })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid purchase price.'
            })
    else:
        purchase_price = None
    
    try:
        # Update the book copy
        copy.copy_number = copy_number
        copy.barcode = barcode if barcode else copy.barcode
        copy.accession_number = accession_number if accession_number else copy.accession_number
        copy.status = status
        copy.condition = condition
        copy.notes = notes
        copy.purchase_date = purchase_date
        copy.purchase_price = purchase_price
        
        # Validate and save
        copy.full_clean()
        copy.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Copy {copy_number} updated successfully.',
            'copy': {
                'id': copy.id,
                'book_id': copy.book.id,
                'book_title': copy.book.title,
                'copy_number': copy.copy_number,
                'barcode': copy.barcode,
                'accession_number': copy.accession_number,
                'status': copy.status,
                'status_display': copy.get_status_display(),
                'condition': copy.condition,
                'condition_display': copy.get_condition_display(),
                'notes': copy.notes,
                'purchase_date': copy.purchase_date.strftime('%b %d, %Y') if copy.purchase_date else '',
                'purchase_price': float(copy.purchase_price) if copy.purchase_price else None,
                'updated_at': copy.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'barcode' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'Another copy with barcode "{barcode}" already exists.'
                })
            elif 'accession_number' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': f'Another copy with accession number "{accession_number}" already exists.'
                })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating copy: {str(e)}'
        })


def toggle_copy_status(request):
    """Toggle copy status between available and unavailable"""
    copy_id = request.POST.get('id')
    if not copy_id:
        return JsonResponse({
            'success': False,
            'message': 'Copy ID is required.'
        })
    
    try:
        copy = BookCopy.objects.get(id=copy_id)
    except BookCopy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Copy not found.'
        })
    
    # Toggle status between available and borrowed
    if copy.status == 'available':
        # Check if copy is already borrowed
        active_borrows = BookBorrow.objects.filter(
            book_copy=copy,
            status__in=['active', 'overdue']
        ).exists()
        
        if active_borrows:
            return JsonResponse({
                'success': False,
                'message': f'Cannot mark as unavailable. Copy is currently borrowed.'
            })
        
        copy.status = 'unavailable'
        action = 'marked as unavailable'
    elif copy.status == 'unavailable':
        copy.status = 'available'
        action = 'marked as available'
    else:
        # For other statuses, toggle to available
        copy.status = 'available'
        action = 'marked as available'
    
    try:
        copy.save()
        return JsonResponse({
            'success': True,
            'message': f'Copy {copy.copy_number} of "{copy.book.title}" {action}.',
            'status': copy.status,
            'status_display': copy.get_status_display()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating copy status: {str(e)}'
        })


def delete_book_copy(request):
    """Delete a book copy"""
    copy_id = request.POST.get('id')
    if not copy_id:
        return JsonResponse({
            'success': False,
            'message': 'Copy ID is required.'
        })
    
    try:
        copy = BookCopy.objects.get(id=copy_id)
    except BookCopy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Copy not found.'
        })
    
    # Check if copy has active borrows
    active_borrows = BookBorrow.objects.filter(
        book_copy=copy,
        status__in=['active', 'overdue']
    ).exists()
    
    if active_borrows:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete copy {copy.copy_number} because it has active borrows.'
        })
    
    book_title = copy.book.title
    copy_number = copy.copy_number
    
    try:
        copy.delete()
        return JsonResponse({
            'success': True,
            'message': f'Copy {copy_number} of "{book_title}" deleted successfully.',
            'id': copy_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting copy: {str(e)}'
        })


def bulk_create_copies(request):
    """Create multiple copies at once"""
    book_id = request.POST.get('book')
    start_number = request.POST.get('start_number', '1')
    count = request.POST.get('count', '1')
    
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book selection is required.'
        })
    
    # Get book
    try:
        book = Book.objects.get(id=book_id)
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected book does not exist.'
        })
    
    # Validate start number and count
    try:
        # Extract numeric part if it contains letters
        if not start_number.isdigit():
            # Try to extract numbers from the string
            import re
            numbers = re.findall(r'\d+', start_number)
            if numbers:
                start_num = int(numbers[0])
            else:
                raise ValueError("Start number must contain numbers.")
        else:
            start_num = int(start_number)
            
        if start_num < 1:
            return JsonResponse({
                'success': False,
                'message': 'Start number must be at least 1.'
            })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': f'Invalid start number: {str(e)}'
        })
    
    try:
        count_num = int(count)
        if count_num < 1:
            return JsonResponse({
                'success': False,
                'message': 'Count must be at least 1.'
            })
        if count_num > 50:
            return JsonResponse({
                'success': False,
                'message': 'Cannot create more than 50 copies at once.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid count value.'
        })
    
    # Get default status and condition
    status = request.POST.get('status', 'available')
    condition = request.POST.get('condition', 'good')
    notes = request.POST.get('notes', '').strip()
    
    created_copies = []
    errors = []
    
    try:
        # Get existing copies to determine next available numbers
        existing_copies = BookCopy.objects.filter(book=book)
        
        # Find the highest copy number
        import re
        max_copy_num = 0
        for copy in existing_copies:
            numbers = re.findall(r'\d+', copy.copy_number)
            if numbers:
                try:
                    num = int(numbers[0])
                    if num > max_copy_num:
                        max_copy_num = num
                except ValueError:
                    pass
        
        # Find the highest accession number suffix
        base_accession = book.accession_number
        pattern = re.compile(rf'^{re.escape(base_accession)}-C(\d+)$')
        existing_accession_nums = []
        
        for copy in existing_copies:
            match = pattern.match(copy.accession_number)
            if match:
                try:
                    existing_accession_nums.append(int(match.group(1)))
                except ValueError:
                    pass
        
        max_accession_num = max(existing_accession_nums) if existing_accession_nums else 0
        
        # Start from the highest of either start_num or existing numbers
        actual_start = max(start_num, max_copy_num + 1, max_accession_num + 1)
        
        copies_to_create = []
        
        # Generate unique barcodes
        import uuid
        
        for i in range(count_num):
            copy_num = actual_start + i
            # Format as 3-digit number
            copy_number = f"{copy_num:03d}"
            
            # Check if copy number already exists
            if BookCopy.objects.filter(book=book, copy_number=copy_number).exists():
                errors.append(f'Copy number {copy_number} already exists.')
                continue
            
            # Generate unique barcode
            barcode = str(uuid.uuid4().int)[:12]
            
            # Check if barcode already exists (unlikely, but just in case)
            while BookCopy.objects.filter(barcode=barcode).exists():
                barcode = str(uuid.uuid4().int)[:12]
            
            # Generate accession number
            accession_suffix = max_accession_num + i + 1
            accession_number = f"{base_accession}-C{accession_suffix:03d}"
            
            # Create the copy instance with all required fields
            copy = BookCopy(
                book=book,
                copy_number=copy_number,
                barcode=barcode,
                accession_number=accession_number,
                status=status,
                condition=condition,
                notes=notes
            )
            copies_to_create.append(copy)
        
        # Bulk create all copies
        if copies_to_create:
            created_instances = BookCopy.objects.bulk_create(copies_to_create)
            
            for copy in created_instances:
                created_copies.append({
                    'id': copy.id,
                    'copy_number': copy.copy_number,
                    'barcode': copy.barcode,
                    'accession_number': copy.accession_number
                })
        
        if errors:
            return JsonResponse({
                'success': False,
                'message': f'Some copies were not created: {", ".join(errors)}',
                'created_copies': created_copies
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully created {len(created_copies)} copy(ies) for "{book.title}".',
            'created_copies': created_copies
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            if 'accession_number' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': 'Duplicate accession number detected. Please try again.'
                })
            elif 'barcode' in str(e).lower():
                return JsonResponse({
                    'success': False,
                    'message': 'Duplicate barcode detected. Please try again.'
                })
            return JsonResponse({
                'success': False,
                'message': 'Duplicate copy number detected.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating copies: {str(e)}'
        })

@login_required
def get_copy_data(request, copy_id):
    """Get book copy data for editing via AJAX"""
    try:
        copy = BookCopy.objects.select_related('book').get(id=copy_id)
        return JsonResponse({
            'success': True,
            'copy': {
                'id': copy.id,
                'book_id': copy.book.id,
                'book_title': copy.book.title,
                'copy_number': copy.copy_number,
                'barcode': copy.barcode,
                'accession_number': copy.accession_number,
                'status': copy.status,
                'condition': copy.condition,
                'notes': copy.notes,
                'purchase_date': copy.purchase_date.strftime('%Y-%m-%d') if copy.purchase_date else '',
                'purchase_price': float(copy.purchase_price) if copy.purchase_price else None,
            }
        })
    except BookCopy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Copy not found.'
        })

@login_required
def borrowing_rules_list(request):
    """Display borrowing rules management page"""
    rules = BorrowingRules.objects.all().order_by('borrower_type')
    
    # Calculate statistics
    max_books_allowed_sum = rules.aggregate(Avg('max_books_allowed'))['max_books_allowed__avg'] or 0
    renewal_allowed_count = rules.filter(renewal_allowed=True).count()
    can_borrow_reference_count = rules.filter(can_borrow_reference=True).count()
    
    context = {
        'rules': rules,
        'borrower_type_choices': BorrowingRules.BORROWER_TYPE_CHOICES,
        'max_books_allowed_sum': round(max_books_allowed_sum, 1),
        'renewal_allowed_count': renewal_allowed_count,
        'can_borrow_reference_count': can_borrow_reference_count,
    }
    
    return render(request, 'admin/library/borrowing_rules_list.html', context)


@login_required
def borrowing_rules_crud(request):
    """Handle AJAX CRUD operations for borrowing rules"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_borrowing_rule(request)
            elif action == 'update':
                return update_borrowing_rule(request)
            elif action == 'delete':
                return delete_borrowing_rule(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def create_borrowing_rule(request):
    """Create a new borrowing rule"""
    # Get and validate required fields
    borrower_type = request.POST.get('borrower_type')
    if not borrower_type:
        return JsonResponse({
            'success': False,
            'message': 'Borrower type is required.'
        })
    
    # Check if rule already exists for this borrower type
    if BorrowingRules.objects.filter(borrower_type=borrower_type).exists():
        return JsonResponse({
            'success': False,
            'message': f'Rules for {borrower_type} already exist.'
        })
    
    # Get and validate numeric fields
    try:
        max_books_allowed = int(request.POST.get('max_books_allowed', 1))
        if max_books_allowed < 1 or max_books_allowed > 10:
            return JsonResponse({
                'success': False,
                'message': 'Maximum books allowed must be between 1 and 10.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid maximum books allowed value.'
        })
    
    try:
        borrowing_duration_days = int(request.POST.get('borrowing_duration_days', 7))
        if borrowing_duration_days < 1 or borrowing_duration_days > 30:
            return JsonResponse({
                'success': False,
                'message': 'Borrowing duration must be between 1 and 30 days.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid borrowing duration value.'
        })
    
    try:
        fine_per_day = Decimal(request.POST.get('fine_per_day', 500.00))
        if fine_per_day < 0:
            return JsonResponse({
                'success': False,
                'message': 'Fine per day cannot be negative.'
            })
    except (ValueError, InvalidOperation):
        return JsonResponse({
            'success': False,
            'message': 'Invalid fine per day value.'
        })
    
    try:
        max_fine_amount = Decimal(request.POST.get('max_fine_amount', 10000.00))
        if max_fine_amount < 0:
            return JsonResponse({
                'success': False,
                'message': 'Maximum fine amount cannot be negative.'
            })
    except (ValueError, InvalidOperation):
        return JsonResponse({
            'success': False,
            'message': 'Invalid maximum fine amount value.'
        })
    
    if fine_per_day > max_fine_amount:
        return JsonResponse({
            'success': False,
            'message': 'Fine per day cannot exceed maximum fine amount.'
        })
    
    # Get boolean fields
    renewal_allowed = request.POST.get('renewal_allowed') == 'on' or request.POST.get('renewal_allowed') == 'true'
    can_borrow_reference = request.POST.get('can_borrow_reference') == 'on' or request.POST.get('can_borrow_reference') == 'true'
    
    # Get optional renewal fields
    max_renewals = 1
    renewal_duration_days = 7
    
    if renewal_allowed:
        try:
            max_renewals = int(request.POST.get('max_renewals', 1))
            if max_renewals < 0 or max_renewals > 5:
                return JsonResponse({
                    'success': False,
                    'message': 'Maximum renewals must be between 0 and 5.'
                })
        except ValueError:
            max_renewals = 1
        
        try:
            renewal_duration_days = int(request.POST.get('renewal_duration_days', 7))
            if renewal_duration_days < 1 or renewal_duration_days > 30:
                return JsonResponse({
                    'success': False,
                    'message': 'Renewal duration must be between 1 and 30 days.'
                })
        except ValueError:
            renewal_duration_days = 7
    
    try:
        # Create the borrowing rule
        rule = BorrowingRules.objects.create(
            borrower_type=borrower_type,
            max_books_allowed=max_books_allowed,
            borrowing_duration_days=borrowing_duration_days,
            renewal_allowed=renewal_allowed,
            max_renewals=max_renewals,
            renewal_duration_days=renewal_duration_days,
            fine_per_day=fine_per_day,
            max_fine_amount=max_fine_amount,
            can_borrow_reference=can_borrow_reference
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Borrowing rules for {rule.get_borrower_type_display()} created successfully.',
            'rule': {
                'id': rule.id,
                'borrower_type': rule.borrower_type,
                'borrower_type_display': rule.get_borrower_type_display(),
                'max_books_allowed': rule.max_books_allowed,
                'borrowing_duration_days': rule.borrowing_duration_days,
                'renewal_allowed': rule.renewal_allowed,
                'max_renewals': rule.max_renewals,
                'renewal_duration_days': rule.renewal_duration_days,
                'fine_per_day': float(rule.fine_per_day),
                'max_fine_amount': float(rule.max_fine_amount),
                'can_borrow_reference': rule.can_borrow_reference,
                'created_at': rule.created_at.strftime('%b %d, %Y'),
                'updated_at': rule.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'Rules for {borrower_type} already exist.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating borrowing rules: {str(e)}'
        })


def update_borrowing_rule(request):
    """Update an existing borrowing rule"""
    rule_id = request.POST.get('id')
    if not rule_id:
        return JsonResponse({
            'success': False,
            'message': 'Rule ID is required.'
        })
    
    try:
        rule = BorrowingRules.objects.get(id=rule_id)
    except BorrowingRules.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Rule not found.'
        })
    
    # Get and validate numeric fields
    try:
        max_books_allowed = int(request.POST.get('max_books_allowed', 1))
        if max_books_allowed < 1 or max_books_allowed > 10:
            return JsonResponse({
                'success': False,
                'message': 'Maximum books allowed must be between 1 and 10.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid maximum books allowed value.'
        })
    
    try:
        borrowing_duration_days = int(request.POST.get('borrowing_duration_days', 7))
        if borrowing_duration_days < 1 or borrowing_duration_days > 30:
            return JsonResponse({
                'success': False,
                'message': 'Borrowing duration must be between 1 and 30 days.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid borrowing duration value.'
        })
    
    try:
        fine_per_day = Decimal(request.POST.get('fine_per_day', 500.00))
        if fine_per_day < 0:
            return JsonResponse({
                'success': False,
                'message': 'Fine per day cannot be negative.'
            })
    except (ValueError, InvalidOperation):
        return JsonResponse({
            'success': False,
            'message': 'Invalid fine per day value.'
        })
    
    try:
        max_fine_amount = Decimal(request.POST.get('max_fine_amount', 10000.00))
        if max_fine_amount < 0:
            return JsonResponse({
                'success': False,
                'message': 'Maximum fine amount cannot be negative.'
            })
    except (ValueError, InvalidOperation):
        return JsonResponse({
            'success': False,
            'message': 'Invalid maximum fine amount value.'
        })
    
    if fine_per_day > max_fine_amount:
        return JsonResponse({
            'success': False,
            'message': 'Fine per day cannot exceed maximum fine amount.'
        })
    
    # Get boolean fields
    renewal_allowed = request.POST.get('renewal_allowed') == 'on' or request.POST.get('renewal_allowed') == 'true'
    can_borrow_reference = request.POST.get('can_borrow_reference') == 'on' or request.POST.get('can_borrow_reference') == 'true'
    
    # Get optional renewal fields
    max_renewals = 1
    renewal_duration_days = 7
    
    if renewal_allowed:
        try:
            max_renewals = int(request.POST.get('max_renewals', 1))
            if max_renewals < 0 or max_renewals > 5:
                return JsonResponse({
                    'success': False,
                    'message': 'Maximum renewals must be between 0 and 5.'
                })
        except ValueError:
            max_renewals = 1
        
        try:
            renewal_duration_days = int(request.POST.get('renewal_duration_days', 7))
            if renewal_duration_days < 1 or renewal_duration_days > 30:
                return JsonResponse({
                    'success': False,
                    'message': 'Renewal duration must be between 1 and 30 days.'
                })
        except ValueError:
            renewal_duration_days = 7
    else:
        max_renewals = 0
        renewal_duration_days = 0
    
    try:
        # Update the borrowing rule
        rule.max_books_allowed = max_books_allowed
        rule.borrowing_duration_days = borrowing_duration_days
        rule.renewal_allowed = renewal_allowed
        rule.max_renewals = max_renewals
        rule.renewal_duration_days = renewal_duration_days
        rule.fine_per_day = fine_per_day
        rule.max_fine_amount = max_fine_amount
        rule.can_borrow_reference = can_borrow_reference
        
        rule.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Borrowing rules for {rule.get_borrower_type_display()} updated successfully.',
            'rule': {
                'id': rule.id,
                'borrower_type': rule.borrower_type,
                'borrower_type_display': rule.get_borrower_type_display(),
                'max_books_allowed': rule.max_books_allowed,
                'borrowing_duration_days': rule.borrowing_duration_days,
                'renewal_allowed': rule.renewal_allowed,
                'max_renewals': rule.max_renewals,
                'renewal_duration_days': rule.renewal_duration_days,
                'fine_per_day': float(rule.fine_per_day),
                'max_fine_amount': float(rule.max_fine_amount),
                'can_borrow_reference': rule.can_borrow_reference,
                'updated_at': rule.updated_at.strftime('%b %d, %Y')
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating borrowing rules: {str(e)}'
        })


def delete_borrowing_rule(request):
    """Delete a borrowing rule"""
    rule_id = request.POST.get('id')
    if not rule_id:
        return JsonResponse({
            'success': False,
            'message': 'Rule ID is required.'
        })
    
    try:
        rule = BorrowingRules.objects.get(id=rule_id)
    except BorrowingRules.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Rule not found.'
        })
    
    borrower_type_display = rule.get_borrower_type_display()
    
    try:
        rule.delete()
        return JsonResponse({
            'success': True,
            'message': f'Borrowing rules for {borrower_type_display} deleted successfully.',
            'id': rule_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting borrowing rules: {str(e)}'
        })


@login_required
def get_borrowing_rule_data(request, rule_id):
    """Get borrowing rule data for editing via AJAX"""
    try:
        rule = BorrowingRules.objects.get(id=rule_id)
        return JsonResponse({
            'success': True,
            'rule': {
                'id': rule.id,
                'borrower_type': rule.borrower_type,
                'max_books_allowed': rule.max_books_allowed,
                'borrowing_duration_days': rule.borrowing_duration_days,
                'renewal_allowed': rule.renewal_allowed,
                'max_renewals': rule.max_renewals,
                'renewal_duration_days': rule.renewal_duration_days,
                'fine_per_day': float(rule.fine_per_day),
                'max_fine_amount': float(rule.max_fine_amount),
                'can_borrow_reference': rule.can_borrow_reference,
            }
        })
    except BorrowingRules.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Rule not found.'
        })        


# accounts/views/library_admin_views.py - Add these functions

@login_required
def book_borrows_list(request):
    """Display book borrows management page with support for both staff and students"""
    # Start with all borrows
    borrows = BookBorrow.objects.select_related(
        'book', 'staff_borrower', 'student_borrower', 'book_copy', 'issued_by'
    ).prefetch_related(
        'book__category',
        'fine_payments'
    ).order_by('-borrow_date', '-created_at')
    
    # Get all available filters from request
    status_filter = request.GET.get('status', '')
    borrower_type_filter = request.GET.get('borrower_type', '')
    borrower_filter = request.GET.get('borrower', '')
    book_filter = request.GET.get('book', '')
    date_range_filter = request.GET.get('date_range', '')
    fine_status_filter = request.GET.get('fine_status', '')
    renewal_status_filter = request.GET.get('renewal_status', '')
    issued_by_filter = request.GET.get('issued_by', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if status_filter:
        borrows = borrows.filter(status=status_filter)
    
    if borrower_type_filter:
        if borrower_type_filter == 'staff':
            borrows = borrows.filter(borrower_type='staff')
        elif borrower_type_filter == 'student':
            borrows = borrows.filter(borrower_type='student')
    
    if borrower_filter:
        # Search in both staff and student borrowers
        borrows = borrows.filter(
            Q(staff_borrower__admin__username__icontains=borrower_filter) |
            Q(staff_borrower__admin__first_name__icontains=borrower_filter) |
            Q(staff_borrower__admin__last_name__icontains=borrower_filter) |
            Q(student_borrower__first_name__icontains=borrower_filter) |
            Q(student_borrower__last_name__icontains=borrower_filter) |
            Q(student_borrower__registration_number__icontains=borrower_filter)
        )
    
    if book_filter:
        borrows = borrows.filter(
            Q(book__title__icontains=book_filter) |
            Q(book__author__icontains=book_filter) |
            Q(book__isbn__icontains=book_filter) |
            Q(book__accession_number__icontains=book_filter)
        )
    
    if issued_by_filter:
        borrows = borrows.filter(issued_by__username__icontains=issued_by_filter)
    
    # Apply date range filter
    if date_range_filter:
        today = timezone.now().date()
        
        if date_range_filter == 'today':
            borrows = borrows.filter(borrow_date=today)
        elif date_range_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            borrows = borrows.filter(borrow_date=yesterday)
        elif date_range_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            borrows = borrows.filter(borrow_date__gte=start_of_week)
        elif date_range_filter == 'last_week':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            borrows = borrows.filter(borrow_date__range=[start_of_last_week, end_of_last_week])
        elif date_range_filter == 'this_month':
            start_of_month = today.replace(day=1)
            borrows = borrows.filter(borrow_date__gte=start_of_month)
        elif date_range_filter == 'last_month':
            first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            borrows = borrows.filter(borrow_date__range=[first_day_of_last_month, last_day_of_last_month])
        elif date_range_filter == 'last_30_days':
            thirty_days_ago = today - timedelta(days=30)
            borrows = borrows.filter(borrow_date__gte=thirty_days_ago)
        elif date_range_filter == 'last_90_days':
            ninety_days_ago = today - timedelta(days=90)
            borrows = borrows.filter(borrow_date__gte=ninety_days_ago)
        elif date_range_filter == 'this_year':
            start_of_year = today.replace(month=1, day=1)
            borrows = borrows.filter(borrow_date__gte=start_of_year)
    
    # Apply custom date range
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            borrows = borrows.filter(borrow_date__range=[from_date, to_date])
        except ValueError:
            pass
    
    # Apply fine status filter
    if fine_status_filter:
        if fine_status_filter == 'with_fine':
            borrows = borrows.filter(fine_amount__gt=0)
        elif fine_status_filter == 'no_fine':
            borrows = borrows.filter(fine_amount=0)
        elif fine_status_filter == 'paid':
            borrows = borrows.filter(fine_balance=0, fine_amount__gt=0)
        elif fine_status_filter == 'partial':
            borrows = borrows.filter(fine_balance__gt=0, fine_balance__lt=F('fine_amount'))
    
    # Apply renewal status filter
    if renewal_status_filter:
        if renewal_status_filter == 'renewed':
            borrows = borrows.filter(renewed_count__gt=0)
        elif renewal_status_filter == 'not_renewed':
            borrows = borrows.filter(renewed_count=0)
        elif renewal_status_filter == 'can_renew':
            # Borrows that are active and have renewals left (assuming max 2 renewals)
            borrows = borrows.filter(status='active', renewed_count__lt=2)
    
    # Calculate comprehensive statistics
    total_borrows = borrows.count()
    
    # Status-based counts
    active_borrows_count = borrows.filter(status='active').count()
    overdue_borrows_count = borrows.filter(status='overdue').count()
    returned_borrows_count = borrows.filter(status='returned').count()
    lost_borrows_count = borrows.filter(status='lost').count()
    cancelled_borrows_count = borrows.filter(status='cancelled').count()
    
    # Borrower type counts
    staff_borrows_count = borrows.filter(borrower_type='staff').count()
    student_borrows_count = borrows.filter(borrower_type='student').count()
    
    # Fine statistics
    total_fine_amount = borrows.aggregate(total=Sum('fine_amount'))['total'] or 0
    total_fine_paid = borrows.aggregate(total=Sum('fine_paid'))['total'] or 0
    total_fine_balance = borrows.aggregate(total=Sum('fine_balance'))['total'] or 0
    
    # Renewal statistics
    renewed_borrows_count = borrows.filter(renewed_count__gt=0).count()
    avg_renewals = borrows.aggregate(avg=Avg('renewed_count'))['avg'] or 0
    
    # Get unique values for filters
    unique_books = Book.objects.filter(
        id__in=borrows.values_list('book_id', flat=True).distinct()
    ).values('id', 'title').order_by('title')
    
    unique_issuers = Staffs.objects.filter(
        id__in=borrows.values_list('issued_by_id', flat=True).distinct()
    ).select_related('admin').order_by('admin__username')
    
    # Get status choices
    status_choices = BookBorrow.BORROW_STATUS_CHOICES
    
    # Prepare context for template
    context = {
        'borrows': borrows,
        'total_borrows': total_borrows,
        
        # Status statistics
        'active_borrows_count': active_borrows_count,
        'overdue_borrows_count': overdue_borrows_count,
        'returned_borrows_count': returned_borrows_count,
        'lost_borrows_count': lost_borrows_count,
        'cancelled_borrows_count': cancelled_borrows_count,
        
        # Borrower type statistics
        'staff_borrows_count': staff_borrows_count,
        'student_borrows_count': student_borrows_count,
        
        # Fine statistics
        'total_fine_amount': total_fine_amount,
        'total_fine_paid': total_fine_paid,
        'total_fine_balance': total_fine_balance,
        
        # Renewal statistics
        'renewed_borrows_count': renewed_borrows_count,
        'avg_renewals': round(avg_renewals, 1),
        
        # Filter options
        'status_choices': status_choices,
        'unique_books': unique_books,
        'unique_issuers': unique_issuers,
        
        # Current filter values (for form persistence)
        'status_filter': status_filter,
        'borrower_type_filter': borrower_type_filter,
        'borrower_filter': borrower_filter,
        'book_filter': book_filter,
        'date_range_filter': date_range_filter,
        'fine_status_filter': fine_status_filter,
        'renewal_status_filter': renewal_status_filter,
        'issued_by_filter': issued_by_filter,
        'date_from': date_from,
        'date_to': date_to,
        
        # Tomorrow for due soon highlighting
        'tomorrow': timezone.now().date() + timedelta(days=1),
        
        # Filter options for dropdowns
        'date_range_options': [
            ('', 'All Time'),
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('last_30_days', 'Last 30 Days'),
            ('last_90_days', 'Last 90 Days'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        
        'fine_status_options': [
            ('', 'All'),
            ('with_fine', 'With Fine'),
            ('no_fine', 'No Fine'),
            ('paid', 'Fully Paid'),
            ('partial', 'Partially Paid'),
        ],
        
        'renewal_status_options': [
            ('', 'All'),
            ('renewed', 'Renewed'),
            ('not_renewed', 'Not Renewed'),
            ('can_renew', 'Can Renew'),
        ],
        
        'borrower_type_options': [
            ('', 'All Types'),
            ('staff', 'Staff'),
            ('student', 'Student'),
        ],
    }
    
    return render(request, 'admin/library/book_borrows_list.html', context)




@login_required
def create_book_borrow_view(request):
    """Display form to create a new book borrow for both staff and students"""
    if request.method == 'POST':
        return create_book_borrow(request)
    
    # Get available data for form
    available_books = Book.objects.filter(
        status='available',
        available_copies__gt=0
    ).order_by('title')
    
    # Get all staff and students
    staff_borrowers = Staffs.objects.filter(admin__is_active=True).order_by('admin__username')
    student_borrowers = Student.objects.filter(is_active=True, status='active').order_by('first_name')
    
    # Get borrowing rules for reference
    borrowing_rules = BorrowingRules.objects.all()
    
    # Get available copies for JavaScript
    available_copies = BookCopy.objects.filter(
        status='available'
    ).select_related('book').order_by('book__title', 'copy_number')
    
    # Prepare copies data for JavaScript
    copies_data = {}
    for copy in available_copies:
        if copy.book.id not in copies_data:
            copies_data[copy.book.id] = []
        copies_data[copy.book.id].append({
            'id': copy.id,
            'copy_number': copy.copy_number,
            'accession_number': copy.accession_number,
            'condition': copy.get_condition_display(),
            'barcode': copy.barcode
        })
    
    context = {
        'available_books': available_books,
        'staff_borrowers': staff_borrowers,
        'student_borrowers': student_borrowers,
        'borrowing_rules': borrowing_rules,
        'copies_json': json.dumps(copies_data),
    }
    
    return render(request, 'admin/library/create_book_borrow.html', context)


def create_book_borrow(request):
    """Create a new book borrow record for both staff and students"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'POST request required.'
        })
    
    try:
        # Get borrower type and ID
        borrower_type = request.POST.get('borrower_type')
        borrower_id = request.POST.get('borrower_id')
        
        # Get book details
        book_id = request.POST.get('book')
        book_copy_id = request.POST.get('book_copy', '').strip()
        
        if not borrower_type or not borrower_id or not book_id:
            return JsonResponse({
                'success': False,
                'message': 'Borrower type, Borrower, and Book are required.'
            })
        
        # Get borrower based on type
        if borrower_type == 'staff':
            try:
                borrower = Staffs.objects.get(id=borrower_id)
            except Staffs.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected staff does not exist.'
                })
        elif borrower_type == 'student':
            try:
                borrower = Student.objects.get(id=borrower_id)
            except Student.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected student does not exist.'
                })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid borrower type.'
            })
        
        # Get book
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected book does not exist.'
            })
        
        # Get book copy if specified
        book_copy = None
        if book_copy_id:
            try:
                book_copy = BookCopy.objects.get(id=book_copy_id, book=book)
                if not book_copy.is_available():
                    return JsonResponse({
                        'success': False,
                        'message': 'Selected copy is not available.'
                    })
            except BookCopy.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected copy does not exist.'
                })
        
        # Check if book is available
        if not book.is_available():
            return JsonResponse({
                'success': False,
                'message': 'Book is not available for borrowing.'
            })
        
        # Check borrower eligibility
        from library.models import check_borrower_eligibility
        
        # Get user object for eligibility check
        if borrower_type == 'staff':
            user = borrower.admin
        else:
            # For student, we need a user object - you might need to adjust this
            # based on how your Student model relates to User
            user = None
            # If Student has a user field, use it. Otherwise, create a dummy check
            if hasattr(borrower, 'user'):
                user = borrower.user
            else:
                # Alternative eligibility check for students without user
                rules_type = 'student' if borrower_type == 'student' else 'teacher'
                try:
                    rules = BorrowingRules.objects.get(borrower_type=rules_type)
                except BorrowingRules.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'No borrowing rules found for this user type.'
                    })
                
                # Check active borrows manually
                if borrower_type == 'student':
                    active_borrows = BookBorrow.objects.filter(
                        student_borrower=borrower,
                        status__in=['active', 'overdue']
                    ).count()
                else:
                    active_borrows = BookBorrow.objects.filter(
                        staff_borrower=borrower,
                        status__in=['active', 'overdue']
                    ).count()
                
                if active_borrows >= rules.max_books_allowed:
                    return JsonResponse({
                        'success': False,
                        'message': f'You can only borrow {rules.max_books_allowed} book(s) at a time.'
                    })
                
                if book.is_reference and not rules.can_borrow_reference:
                    return JsonResponse({
                        'success': False,
                        'message': 'Reference books cannot be borrowed.'
                    })
        
        # If user exists, use the check_borrower_eligibility function
        if user:
            is_eligible, message = check_borrower_eligibility(user, book)
            if not is_eligible:
                return JsonResponse({
                    'success': False,
                    'message': message
                })
        
        # Determine due date based on borrower type
        rules_type = 'student' if borrower_type == 'student' else 'teacher'
        try:
            rules = BorrowingRules.objects.get(borrower_type=rules_type)
            due_date = datetime.now().date() + timedelta(days=rules.borrowing_duration_days)
        except BorrowingRules.DoesNotExist:
            due_date = datetime.now().date() + timedelta(days=14)  # Default 14 days
        
        # Create the borrow record
        borrow_data = {
            'borrower_type': borrower_type,
            'book': book,
            'book_copy': book_copy,
            'due_date': due_date,
            'issued_by': request.user.staff if hasattr(request.user, 'staff') else None,
            'status': 'active',
            'borrowed_book_title': book.title,
            'borrowed_book_author': book.author,
            'borrowed_accession_number': book.accession_number,
            'borrowed_barcode': book.barcode,
        }
        
        # Set the appropriate borrower field
        if borrower_type == 'staff':
            borrow_data['staff_borrower'] = borrower
        else:
            borrow_data['student_borrower'] = borrower
        
        borrow = BookBorrow.objects.create(**borrow_data)
        
        # Update book status
        if book_copy:
            book_copy.status = 'borrowed'
            book_copy.save()
        
        # Update book copies count
        book.borrowed_copies += 1
        book.available_copies = book.total_copies - book.borrowed_copies
        if book.available_copies == 0:
            book.status = 'borrowed'
        book.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Book "{book.title}" borrowed successfully by {borrow.get_borrower_name()}. Due date: {due_date.strftime("%b %d, %Y")}',
            'borrow_id': borrow.id,
            'due_date': due_date.strftime('%b %d, %Y')
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating borrow record: {str(e)}'
        })


@login_required
def get_book_copies(request):
    """Get available copies for a specific book via AJAX"""
    book_id = request.GET.get('book_id')
    
    if not book_id:
        return JsonResponse({
            'success': False,
            'message': 'Book ID is required.'
        })
    
    try:
        book = Book.objects.get(id=book_id)
        copies = BookCopy.objects.filter(
            book=book,
            status='available'
        ).order_by('copy_number')
        
        copies_data = []
        for copy in copies:
            copies_data.append({
                'id': copy.id,
                'copy_number': copy.copy_number,
                'accession_number': copy.accession_number,
                'barcode': copy.barcode,
                'condition': copy.get_condition_display(),
                'display_text': f"Copy #{copy.copy_number} - {copy.accession_number} ({copy.get_condition_display()})"
            })
        
        return JsonResponse({
            'success': True,
            'copies': copies_data,
            'book_title': book.title,
            'available_copies': book.available_copies
        })
        
    except Book.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Book not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching copies: {str(e)}'
        })


@login_required
def get_borrower_info(request):
    """Get borrower information and borrowing rules via AJAX"""
    borrower_type = request.GET.get('borrower_type')
    borrower_id = request.GET.get('borrower_id')
    
    if not borrower_type or not borrower_id:
        return JsonResponse({
            'success': False,
            'message': 'Borrower type and ID are required.'
        })
    
    try:
        # Get borrower
        if borrower_type == 'staff':
            borrower = Staffs.objects.get(id=borrower_id)
            borrower_name = borrower.get_full_name()
            # Get borrowing rules for staff (using teacher rules)
            rules_type = 'teacher'
        else:
            borrower = Student.objects.get(id=borrower_id)
            borrower_name = borrower.full_name
            # Get borrowing rules for students
            rules_type = 'student'
        
        # Get active borrows
        if borrower_type == 'staff':
            active_borrows = BookBorrow.objects.filter(
                staff_borrower=borrower,
                status__in=['active', 'overdue']
            ).count()
        else:
            active_borrows = BookBorrow.objects.filter(
                student_borrower=borrower,
                status__in=['active', 'overdue']
            ).count()
        
        # Get borrowing rules
        try:
            rules = BorrowingRules.objects.get(borrower_type=rules_type)
            rules_info = {
                'max_books_allowed': rules.max_books_allowed,
                'borrowing_duration_days': rules.borrowing_duration_days,
                'renewal_allowed': rules.renewal_allowed,
                'max_renewals': rules.max_renewals,
                'renewal_duration_days': rules.renewal_duration_days,
                'fine_per_day': float(rules.fine_per_day),
                'max_fine_amount': float(rules.max_fine_amount),
                'can_borrow_reference': rules.can_borrow_reference,
            }
        except BorrowingRules.DoesNotExist:
            rules_info = None
        
        # Calculate due date
        due_date = None
        if rules_info:
            due_date = (datetime.now().date() + timedelta(days=rules_info['borrowing_duration_days'])).strftime('%Y-%m-%d')
        
        return JsonResponse({
            'success': True,
            'borrower_name': borrower_name,
            'active_borrows': active_borrows,
            'rules': rules_info,
            'due_date': due_date,
            'can_borrow_more': rules_info['max_books_allowed'] > active_borrows if rules_info else True
        })
        
    except (Staffs.DoesNotExist, Student.DoesNotExist):
        return JsonResponse({
            'success': False,
            'message': 'Borrower not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching borrower info: {str(e)}'
        })

@login_required
def return_book_borrow_view(request, borrow_id):
    """Display form to return a borrowed book"""
    try:
        borrow = BookBorrow.objects.select_related('book', 'book_copy').get(id=borrow_id)
        
        if request.method == 'POST':
            return return_book_borrow(request, borrow)
        
        # Calculate current fine
        borrow.update_fine()
        
        # Get condition choices
        condition_choices = BookCopy._meta.get_field('condition').choices
        
        context = {
            'borrow': borrow,
            'condition_choices': condition_choices,
        }
        
        return render(request, 'admin/library/return_book_borrow.html', context)
        
    except BookBorrow.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')


def return_book_borrow(request, borrow):
    """Process book return"""
    try:
        # Get return data
        return_date_str = request.POST.get('return_date')
        condition = request.POST.get('condition', 'good')
        notes = request.POST.get('notes', '').strip()
        
        # Parse return date
        return_date = None
        if return_date_str:
            try:
                return_date = date.fromisoformat(return_date_str)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid return date format. Use YYYY-MM-DD.'
                })
        
        # Return the book
        borrow.return_book(
            return_date=return_date,
            condition=condition,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Book "{borrow.book.title}" returned successfully.',
            'fine_amount': float(borrow.fine_amount),
            'fine_balance': float(borrow.fine_balance)
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error returning book: {str(e)}'
        })


@login_required
def renew_book_borrow_view(request, borrow_id):
    """Display form to renew a book borrow"""
    try:
        borrow = BookBorrow.objects.select_related('book', 'borrower').get(id=borrow_id)
        
        if request.method == 'POST':
            return renew_book_borrow(request, borrow)
        
        # Calculate current status
        borrow.update_fine()
        
        # Get borrower type for rules
        borrower_type = 'staff'  # Default for Staffs model
        
        context = {
            'borrow': borrow,
            'borrower_type': borrower_type,
        }
        
        return render(request, 'admin/library/renew_book_borrow.html', context)
        
    except BookBorrow.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')


def renew_book_borrow(request, borrow):
    """Process book renewal"""
    try:
        # Get renewal reason
        reason = request.POST.get('reason', '').strip()
        
        # Renew the book
        borrow.renew_book(renewed_by=request.user)
        
        # Create renewal record with reason
        from library.models import BookRenewal
        BookRenewal.objects.create(
            borrow=borrow,
            renewed_by=request.user,
            previous_due_date=borrow.due_date - timedelta(days=7),  # Assuming 7-day renewal
            new_due_date=borrow.due_date,
            reason=reason
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Book "{borrow.book.title}" renewed successfully. New due date: {borrow.due_date.strftime("%b %d, %Y")}',
            'new_due_date': borrow.due_date.strftime('%b %d, %Y')
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error renewing book: {str(e)}'
        })


@login_required
def book_borrows_crud(request):
    """Handle AJAX CRUD operations for book borrows"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'update_status':
                return update_borrow_status(request)
            elif action == 'update_fine':
                return update_borrow_fine(request)
            elif action == 'delete':
                return delete_book_borrow(request)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified.'
                })
                
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'POST request required.'
    })


def update_borrow_status(request):
    """Update borrow status"""
    borrow_id = request.POST.get('id')
    new_status = request.POST.get('status')
    
    if not borrow_id or not new_status:
        return JsonResponse({
            'success': False,
            'message': 'Borrow ID and status are required.'
        })
    
    try:
        borrow = BookBorrow.objects.get(id=borrow_id)
        
        # Validate status change
        valid_transitions = {
            'active': ['returned', 'overdue', 'lost', 'cancelled'],
            'overdue': ['returned', 'lost'],
            'returned': [],  # Cannot change from returned
            'lost': ['returned'],  # Can mark as returned if found
            'cancelled': []  # Cannot change from cancelled
        }
        
        if new_status not in valid_transitions.get(borrow.status, []):
            return JsonResponse({
                'success': False,
                'message': f'Cannot change status from {borrow.status} to {new_status}.'
            })
        
        # Special handling for specific status changes
        if new_status == 'returned':
            # Set actual return date to today
            borrow.actual_return_date = date.today()
            borrow.update_fine()
        
        borrow.status = new_status
        borrow.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {borrow.get_status_display()}.',
            'status': borrow.status,
            'status_display': borrow.get_status_display()
        })
        
    except BookBorrow.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Borrow record not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        })


def update_borrow_fine(request):
    """Update borrow fine amount"""
    borrow_id = request.POST.get('id')
    fine_amount = request.POST.get('fine_amount')
    
    if not borrow_id:
        return JsonResponse({
            'success': False,
            'message': 'Borrow ID is required.'
        })
    
    try:
        borrow = BookBorrow.objects.get(id=borrow_id)
        
        if fine_amount:
            try:
                fine_amount = Decimal(fine_amount)
                if fine_amount < 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'Fine amount cannot be negative.'
                    })
                
                borrow.fine_amount = fine_amount
                borrow.fine_balance = fine_amount - borrow.fine_paid
                borrow.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Fine amount updated to TZS {fine_amount:,.2f}.',
                    'fine_amount': float(borrow.fine_amount),
                    'fine_balance': float(borrow.fine_balance)
                })
                
            except (ValueError, InvalidOperation):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid fine amount.'
                })
        else:
            # Recalculate fine based on overdue days
            borrow.update_fine()
            
            return JsonResponse({
                'success': True,
                'message': f'Fine recalculated: TZS {borrow.fine_amount:,.2f}.',
                'fine_amount': float(borrow.fine_amount),
                'fine_balance': float(borrow.fine_balance)
            })
        
    except BookBorrow.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Borrow record not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating fine: {str(e)}'
        })


def delete_book_borrow(request):
    """Delete a book borrow record"""
    borrow_id = request.POST.get('id')
    
    if not borrow_id:
        return JsonResponse({
            'success': False,
            'message': 'Borrow ID is required.'
        })
    
    try:
        borrow = BookBorrow.objects.get(id=borrow_id)
        
        # Check if borrow can be deleted
        if borrow.status in ['active', 'overdue']:
            return JsonResponse({
                'success': False,
                'message': 'Cannot delete active or overdue borrow records. Please return the book first.'
            })
        
        borrow.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Borrow record deleted successfully.',
            'id': borrow_id
        })
        
    except BookBorrow.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Borrow record not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting borrow record: {str(e)}'
        })


@login_required
def get_borrow_data(request):
    """Get detailed borrow data via AJAX"""
    borrow_id = request.GET.get('borrow_id')
    
    if not borrow_id:
        return JsonResponse({
            'success': False,
            'message': 'Borrow ID is required.'
        })
    
    try:
        borrow = BookBorrow.objects.select_related(
            'book', 'staff_borrower', 'student_borrower', 'book_copy', 'issued_by'
        ).get(id=borrow_id)
        
        # Calculate overdue days
        overdue_days = borrow.calculate_overdue_days()
        
        # Get borrower details
        if borrow.borrower_type == 'staff' and borrow.staff_borrower:
            borrower_name = borrow.staff_borrower.get_full_name()
            borrower_email = borrow.staff_borrower.admin.email if borrow.staff_borrower.admin else None
        elif borrow.borrower_type == 'student' and borrow.student_borrower:
            borrower_name = borrow.student_borrower.full_name
            borrower_email = None  # Students may not have email
        else:
            borrower_name = "Unknown"
            borrower_email = None
        
        # Get book copy details
        book_copy_number = borrow.book_copy.copy_number if borrow.book_copy else None
        book_accession_number = borrow.book_copy.accession_number if borrow.book_copy else None
        
        # Get issued by details
        issued_by_name = borrow.issued_by.username if borrow.issued_by else "System"
        
        # Check if can renew
        can_renew = borrow.status == 'active' and borrow.renewed_count < 2
        
        # Check if can return
        can_return = borrow.status in ['active', 'overdue']
        
        return JsonResponse({
            'success': True,
            'borrow': {
                'id': borrow.id,
                'borrower_type': borrow.borrower_type,
                'borrower_name': borrower_name,
                'borrower_email': borrower_email,
                'book_id': borrow.book.id,
                'book_title': borrow.book.title,
                'book_author': borrow.book.author,
                'book_isbn': borrow.book.isbn,
                'book_copy_id': borrow.book_copy.id if borrow.book_copy else None,
                'book_copy_number': book_copy_number,
                'book_accession_number': book_accession_number,
                'borrow_date': borrow.borrow_date.strftime('%Y-%m-%d'),
                'due_date': borrow.due_date.strftime('%Y-%m-%d'),
                'actual_return_date': borrow.actual_return_date.strftime('%Y-%m-%d') if borrow.actual_return_date else None,
                'status': borrow.status,
                'status_display': borrow.get_status_display(),
                'renewed_count': borrow.renewed_count,
                'last_renewal_date': borrow.last_renewal_date.strftime('%Y-%m-%d') if borrow.last_renewal_date else None,
                'fine_amount': float(borrow.fine_amount),
                'fine_paid': float(borrow.fine_paid),
                'fine_balance': float(borrow.fine_balance),
                'fine_notes': borrow.fine_notes,
                'issued_by_id': borrow.issued_by.id if borrow.issued_by else None,
                'issued_by_name': issued_by_name,
                'overdue_days': overdue_days,
                'can_renew': can_renew,
                'can_return': can_return,
                'created_at': borrow.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': borrow.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
        
    except BookBorrow.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Borrow record not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching borrow data: {str(e)}'
        })




@login_required
def fine_payment_view(request, borrow_id):
    """Handle fine payment for a borrow record"""
    from library.models import FinePayment
    from accounts.models import Staffs

    try:
        borrow = BookBorrow.objects.select_related(
            'book', 'staff_borrower', 'student_borrower'
        ).get(id=borrow_id)

        # Check if payment is needed
        if borrow.fine_balance == 0:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'No outstanding balance to pay.'
                })

            messages.info(request, 'No outstanding balance to pay.')
            return redirect('admin_book_borrows_list')

        if request.method == 'POST':
            return process_fine_payment(request, borrow)

        # GET request - show payment form
        payment_method_choices = FinePayment.PAYMENT_METHOD_CHOICES

        payment_history = FinePayment.objects.filter(
            borrow=borrow
        ).order_by('-payment_date')[:5]

        context = {
            'borrow': borrow,
            'payment_method_choices': payment_method_choices,
            'payment_history': payment_history,
        }

        return render(request, 'admin/library/fine_payment.html', context)

    except BookBorrow.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Borrow record not found.'
            })

        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            })

        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('admin_book_borrows_list')


def process_fine_payment(request, borrow):
    """Process fine payment"""
    from library.models import FinePayment
    from accounts.models import Staffs
    
    try:
        # Get payment data
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'cash')
        transaction_id = request.POST.get('transaction_id', '').strip()
        notes = request.POST.get('notes', '').strip()
        
        # Validate required fields
        if not amount:
            return JsonResponse({
                'success': False,
                'message': 'Payment amount is required.'
            })
        
        if not payment_method:
            return JsonResponse({
                'success': False,
                'message': 'Payment method is required.'
            })
        
        try:
            # Validate amount
            amount = Decimal(amount)
            if amount <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Payment amount must be greater than zero.'
                })
            
            if amount > borrow.fine_balance:
                return JsonResponse({
                    'success': False,
                    'message': f'Payment amount (TZS {amount:,.2f}) exceeds outstanding balance (TZS {borrow.fine_balance:,.2f}).'
                })
            
            # Get borrower
            borrower = borrow.get_borrower()
            if not borrower:
                return JsonResponse({
                    'success': False,
                    'message': 'Borrower not found.'
                })
            
            # Get staff processing the payment
            try:
                received_by = request.user.staff
            except AttributeError:
                # Fallback to first available staff
                received_by = Staffs.objects.filter(admin__is_active=True).first()
                if not received_by:
                    return JsonResponse({
                        'success': False,
                        'message': 'No staff member available to process payment.'
                    })
            
            # Validate payment method
            valid_methods = dict(FinePayment.PAYMENT_METHOD_CHOICES).keys()
            if payment_method not in valid_methods:
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid payment method: {payment_method}'
                })
            
            # Create payment record based on borrower type
            payment_data = {
                'borrow': borrow,
                'amount': amount,
                'payment_method': payment_method,
                'transaction_id': transaction_id if transaction_id else None,
                'received_by': received_by,
                'notes': notes,
                'status': 'completed'
            }
            
            # Set payer based on borrower type
            if borrow.borrower_type == 'staff':
                payment_data['payer_type'] = 'staff'
                payment_data['staff_payer'] = borrower
            else:
                payment_data['payer_type'] = 'student'
                payment_data['student_payer'] = borrower
            
            payment = FinePayment.objects.create(**payment_data)
            
            # Update borrow fine information
            borrow.fine_paid += amount
            borrow.fine_balance = borrow.fine_amount - borrow.fine_paid
            borrow.save()
            
            # If fine is fully paid and book is overdue, update status
            if borrow.fine_balance == 0 and borrow.status == 'overdue':
                borrow.status = 'returned' if borrow.actual_return_date else 'active'
                borrow.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Payment of TZS {amount:,.2f} processed successfully.',
                'payment_id': payment.id,
                'receipt_number': payment.receipt_number,
                'amount_paid': float(amount),
                'fine_amount': float(borrow.fine_amount),
                'fine_paid': float(borrow.fine_paid),
                'fine_balance': float(borrow.fine_balance),
                'new_status': borrow.status,
                'status_display': borrow.get_status_display()
            })
            
        except (ValueError, InvalidOperation) as e:
            return JsonResponse({
                'success': False,
                'message': f'Invalid payment amount: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error processing payment: {str(e)}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })
    

@login_required
def view_payment_receipt(request, payment_id):
    """View payment receipt"""
    from library.models import FinePayment
    
    try:
        payment = FinePayment.objects.select_related(
            'borrow', 'borrow__book', 'paid_by', 'received_by'
        ).get(id=payment_id)
        
        # Check permission - only staff or the borrower can view
        if not request.user.is_staff and payment.paid_by != request.user:
            messages.error(request, 'You do not have permission to view this receipt.')
            return redirect('admin_book_borrows_list')
        
        context = {
            'payment': payment,
            'borrow': payment.borrow,
        }
        
        # Return PDF if requested
        if request.GET.get('format') == 'pdf':
            return generate_receipt_pdf(request, payment)
        
        return render(request, 'admin/library/receipt.html', context)
        
    except FinePayment.DoesNotExist:
        messages.error(request, 'Receipt not found.')
        return redirect('admin_book_borrows_list')


def generate_receipt_pdf(request, payment):
    """Generate PDF receipt"""
    from weasyprint import HTML
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    
    context = {
        'payment': payment,
        'borrow': payment.borrow,
        'date': timezone.now(),
    }
    
    html_string = render_to_string('admin/library/receipt_pdf.html', context)
    
    # Create PDF
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f'receipt_{payment.receipt_number}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# accounts/views/library_admin_views.py
@login_required
def view_book_borrow(request, id):
    """View detailed information about a specific book borrow record"""
    try:
        # Get the borrow record with all related data
        borrow = BookBorrow.objects.select_related(
            'book',
            'staff_borrower__admin',
            'student_borrower',
            'book_copy',
            'issued_by__admin'
        ).prefetch_related(
            'renewals',
            'returns',
            'fine_payments'
        ).get(id=id)

        # Calculate additional information
        overdue_days = borrow.calculate_overdue_days()
        can_renew = borrow.status == 'active' and borrow.renewed_count < 2
        can_return = borrow.status in ['active', 'overdue']

        # Get borrower information based on type
        borrower = None
        active_borrows_count = 0

        if borrow.borrower_type == 'staff' and borrow.staff_borrower:
            borrower = borrow.staff_borrower
            active_borrows_count = BookBorrow.objects.filter(
                staff_borrower=borrower,
                status__in=['active', 'overdue']
            ).exclude(id=borrow.id).count()

        elif borrow.borrower_type == 'student' and borrow.student_borrower:
            borrower = borrow.student_borrower
            active_borrows_count = BookBorrow.objects.filter(
                student_borrower=borrower,
                status__in=['active', 'overdue']
            ).exclude(id=borrow.id).count()

        # Get borrowing rules
        rules_type = 'student' if borrow.borrower_type == 'student' else 'teacher'

        try:
            borrowing_rules = BorrowingRules.objects.get(borrower_type=rules_type)
        except BorrowingRules.DoesNotExist:
            borrowing_rules = None

        fine_payments = borrow.fine_payments.all().order_by('-payment_date')
        renewal_history = borrow.renewals.all().order_by('-renewal_date')
        return_history = borrow.returns.all().order_by('-return_date')

        context = {
            'borrow': borrow,
            'borrower': borrower,
            'active_borrows_count': active_borrows_count,
            'overdue_days': overdue_days,
            'can_renew': can_renew,
            'can_return': can_return,
            'borrowing_rules': borrowing_rules,
            'fine_payments': fine_payments,
            'renewal_history': renewal_history,
            'return_history': return_history,
            'now': timezone.now(),
        }

        return render(request, 'admin/library/view_book_borrow.html', context)

    except BookBorrow.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')

    except Exception as e:
        messages.error(request, f'Error loading borrow details: {str(e)}')
        return redirect('admin_book_borrows_list')

    
@login_required
def export_borrow_details_pdf(request, borrow_id):
    """Export detailed borrow information to PDF using WeasyPrint"""
    try:
        # Get the borrow record with all related data
        borrow = BookBorrow.objects.select_related(
            'book',
            'staff_borrower__admin',
            'student_borrower',
            'book_copy',
            'issued_by__admin'
        ).prefetch_related(
            'renewals',
            'returns',
            'fine_payments'
        ).get(id=borrow_id)

        # Calculate additional information
        overdue_days = borrow.calculate_overdue_days()
        
        # Get borrower information based on type
        borrower = None
        active_borrows_count = 0

        if borrow.borrower_type == 'staff' and borrow.staff_borrower:
            borrower = borrow.staff_borrower
            active_borrows_count = BookBorrow.objects.filter(
                staff_borrower=borrower,
                status__in=['active', 'overdue']
            ).exclude(id=borrow.id).count()

        elif borrow.borrower_type == 'student' and borrow.student_borrower:
            borrower = borrow.student_borrower
            active_borrows_count = BookBorrow.objects.filter(
                student_borrower=borrower,
                status__in=['active', 'overdue']
            ).exclude(id=borrow.id).count()

        # Get borrowing rules
        rules_type = 'student' if borrow.borrower_type == 'student' else 'teacher'
        try:
            borrowing_rules = BorrowingRules.objects.get(borrower_type=rules_type)
        except BorrowingRules.DoesNotExist:
            borrowing_rules = None

        fine_payments = borrow.fine_payments.all().order_by('-payment_date')
        renewal_history = borrow.renewals.all().order_by('-renewal_date')
        return_history = borrow.returns.all().order_by('-return_date')
        
        # Prepare context for PDF
        context = {
            'borrow': borrow,
            'borrower': borrower,
            'active_borrows_count': active_borrows_count,
            'overdue_days': overdue_days,
            'borrowing_rules': borrowing_rules,
            'fine_payments': fine_payments,
            'renewal_history': renewal_history,
            'return_history': return_history,
            'export_date': timezone.now(),
            'generated_by': request.user.username,
        }

        # Render HTML template
        html_string = render_to_string('admin/library/reports/borrow_details_pdf.html', context)
        
        # Create PDF using WeasyPrint
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        # Create HTTP response with PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        filename = f'borrow_details_{borrow.book.title.replace(" ", "_")}_{borrow.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except BookBorrow.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('admin_book_borrows_list')


# accounts/views/library_admin_views.py
@login_required
def admin_edit_book_borrow(request, id):
    """Edit an existing book borrow record"""
    try:
        # Get the borrow record
        borrow = BookBorrow.objects.select_related(
            'book',
            'staff_borrower__admin',
            'student_borrower',
            'book_copy',
            'issued_by__admin'
        ).get(id=id)
        
        if request.method == 'POST':
            return update_book_borrow(request, borrow)
        
        # Get all available data for the form
        available_books = Book.objects.all().order_by('title')
        
        # Get staff and students
        staff_borrowers = Staffs.objects.filter(admin__is_active=True).order_by('admin__username')
        student_borrowers = Student.objects.filter(is_active=True, status='active').order_by('first_name')
        
        # Get book copies for the selected book
        book_copies = BookCopy.objects.filter(
            book=borrow.book,
            status='available'
        ).order_by('copy_number')
        
        # Get borrowing rules for reference
        if borrow.borrower_type == 'student':
            rules_type = 'student'
        else:
            rules_type = 'teacher'
        
        try:
            borrowing_rules = BorrowingRules.objects.get(borrower_type=rules_type)
        except BorrowingRules.DoesNotExist:
            borrowing_rules = None
        
        # Calculate current status
        borrow.update_fine()
        
        # Get status choices
        status_choices = BookBorrow.BORROW_STATUS_CHOICES
        
        # Get fine payment history
        fine_payments = borrow.fine_payments.all().order_by('-payment_date')
        
        context = {
            'borrow': borrow,
            'available_books': available_books,
            'staff_borrowers': staff_borrowers,
            'student_borrowers': student_borrowers,
            'book_copies': book_copies,
            'borrowing_rules': borrowing_rules,
            'status_choices': status_choices,
            'fine_payments': fine_payments,
            'now': timezone.now(),
        }
        
        return render(request, 'admin/library/edit_book_borrow.html', context)
        
    except BookBorrow.DoesNotExist:
        messages.error(request, 'Borrow record not found.')
        return redirect('admin_book_borrows_list')
    except Exception as e:
        messages.error(request, f'Error loading borrow edit form: {str(e)}')
        return redirect('admin_book_borrows_list')


def update_book_borrow(request, borrow):
    """Update a book borrow record"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'POST request required.'
        })
    
    try:
        # Get form data
        borrower_type = request.POST.get('borrower_type', borrow.borrower_type)
        borrower_id = request.POST.get('borrower_id')
        book_id = request.POST.get('book', borrow.book.id)
        book_copy_id = request.POST.get('book_copy', '')
        due_date_str = request.POST.get('due_date')
        status = request.POST.get('status', borrow.status)
        notes = request.POST.get('notes', '')
        fine_amount = request.POST.get('fine_amount', '')
        fine_notes = request.POST.get('fine_notes', borrow.fine_notes)
        
        # Validate required fields
        if not book_id:
            return JsonResponse({
                'success': False,
                'message': 'Book is required.'
            })
        
        # Get book
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected book does not exist.'
            })
        
        # Get book copy if specified
        book_copy = None
        if book_copy_id:
            try:
                book_copy = BookCopy.objects.get(id=book_copy_id, book=book)
                # Check if copy is available (unless it's the same copy)
                if book_copy != borrow.book_copy and not book_copy.is_available():
                    return JsonResponse({
                        'success': False,
                        'message': 'Selected copy is not available.'
                    })
            except BookCopy.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected copy does not exist.'
                })
        
        # Parse due date
        due_date = None
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
                if due_date < borrow.borrow_date:
                    return JsonResponse({
                        'success': False,
                        'message': 'Due date cannot be before borrow date.'
                    })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid due date format. Use YYYY-MM-DD.'
                })
        else:
            due_date = borrow.due_date
        
        # Validate status transitions
        valid_status_transitions = {
            'active': ['overdue', 'returned', 'lost', 'cancelled'],
            'overdue': ['returned', 'lost'],
            'returned': [],  # Cannot change from returned
            'lost': ['returned'],  # Can mark as returned if found
            'cancelled': []  # Cannot change from cancelled
        }
        
        if status not in valid_status_transitions.get(borrow.status, []) and status != borrow.status:
            return JsonResponse({
                'success': False,
                'message': f'Cannot change status from {borrow.status} to {status}.'
            })
        
        # Handle status changes
        if status == 'returned' and borrow.status != 'returned':
            # Mark as returned
            borrow.actual_return_date = timezone.now().date()
            # Return the book
            if borrow.book:
                borrow.book.update_copies_on_return()
            if borrow.book_copy:
                borrow.book_copy.status = 'available'
                borrow.book_copy.save()
        
        elif status == 'lost' and borrow.status != 'lost':
            # Mark as lost
            if borrow.book:
                # Update book counts (treat as permanently borrowed)
                borrow.book.borrowed_copies += 1
                borrow.book.available_copies = borrow.book.total_copies - borrow.book.borrowed_copies
                borrow.book.save()
            if borrow.book_copy:
                borrow.book_copy.status = 'lost'
                borrow.book_copy.save()
        
        elif status == 'cancelled' and borrow.status != 'cancelled':
            # Cancel the borrow (only possible before book is taken)
            if borrow.status == 'active':
                # Return the book if it was marked as borrowed
                if borrow.book:
                    borrow.book.update_copies_on_return()
                if borrow.book_copy:
                    borrow.book_copy.status = 'available'
                    borrow.book_copy.save()
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot cancel a borrow that is not active.'
                })
        
        # Update borrower if changed
        if borrower_id:
            if borrower_type == 'staff':
                try:
                    staff_borrower = Staffs.objects.get(id=borrower_id)
                    borrow.staff_borrower = staff_borrower
                    borrow.student_borrower = None
                    borrow.borrower_type = 'staff'
                except Staffs.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Selected staff does not exist.'
                    })
            elif borrower_type == 'student':
                try:
                    student_borrower = Student.objects.get(id=borrower_id)
                    borrow.student_borrower = student_borrower
                    borrow.staff_borrower = None
                    borrow.borrower_type = 'student'
                except Student.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Selected student does not exist.'
                    })
        
        # Update book if changed
        if book != borrow.book:
            # Return the old book
            if borrow.book:
                borrow.book.update_copies_on_return()
            
            # Borrow the new book
            if not book.is_available():
                return JsonResponse({
                    'success': False,
                    'message': 'Selected book is not available.'
                })
            
            borrow.book = book
            book.update_copies_on_borrow()
            
            # Update stored book details
            borrow.borrowed_book_title = book.title
            borrow.borrowed_book_author = book.author
            borrow.borrowed_accession_number = book.accession_number
            borrow.borrowed_barcode = book.barcode
        
        # Update book copy if changed
        if book_copy != borrow.book_copy:
            # Update old copy status
            if borrow.book_copy:
                borrow.book_copy.status = 'available'
                borrow.book_copy.save()
            
            # Update new copy status
            if book_copy:
                book_copy.status = 'borrowed'
                book_copy.save()
            
            borrow.book_copy = book_copy
        
        # Update other fields
        borrow.due_date = due_date
        borrow.status = status
        borrow.fine_notes = fine_notes
        
        # Update fine amount if provided
        if fine_amount:
            try:
                fine_amount_decimal = Decimal(fine_amount)
                if fine_amount_decimal < 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'Fine amount cannot be negative.'
                    })
                borrow.fine_amount = fine_amount_decimal
                borrow.fine_balance = borrow.fine_amount - borrow.fine_paid
            except (ValueError, InvalidOperation):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid fine amount.'
                })
        
        # Save the borrow record
        borrow.save()
        
        # Add note if provided
        if notes:
            # Create a note in the fine_notes field
            current_notes = borrow.fine_notes or ''
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            new_note = f"\n\n[{timestamp}] {notes}"
            borrow.fine_notes = current_notes + new_note
            borrow.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Borrow record updated successfully.',
            'borrow_id': borrow.id,
            'new_status': borrow.status,
            'due_date': borrow.due_date.strftime('%Y-%m-%d')
        })
        
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating borrow record: {str(e)}'
        })

    
@login_required
def export_book_borrows(request):
    """Export book borrows to PDF using WeasyPrint with comprehensive filtering"""
    try:
        # Get all borrows with related data
        borrows = BookBorrow.objects.select_related(
            'book', 
            'staff_borrower__admin', 
            'student_borrower',
            'book_copy',
            'issued_by__admin'
        ).prefetch_related(
            'book__category',
            'fine_payments'
        ).order_by('-borrow_date', '-created_at')
        
        # Initialize filters dictionary
        filters = {}
        
        # Get filter parameters from request
        status_filter = request.GET.get('status', '')
        borrower_type_filter = request.GET.get('borrower_type', '')
        borrower_filter = request.GET.get('borrower', '')
        book_filter = request.GET.get('book', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        date_range = request.GET.get('date_range', '')
        
        # Apply status filter
        if status_filter:
            borrows = borrows.filter(status=status_filter)
            filters['status'] = dict(BookBorrow.BORROW_STATUS_CHOICES).get(status_filter, status_filter)
        
        # Apply borrower type filter
        if borrower_type_filter:
            borrows = borrows.filter(borrower_type=borrower_type_filter)
            filters['borrower_type'] = borrower_type_filter
        
        # Apply borrower search filter
        if borrower_filter:
            borrows = borrows.filter(
                Q(staff_borrower__admin__username__icontains=borrower_filter) |
                Q(staff_borrower__admin__first_name__icontains=borrower_filter) |
                Q(staff_borrower__admin__last_name__icontains=borrower_filter) |
                Q(student_borrower__first_name__icontains=borrower_filter) |
                Q(student_borrower__last_name__icontains=borrower_filter) |
                Q(student_borrower__registration_number__icontains=borrower_filter)
            )
            filters['borrower'] = borrower_filter
        
        # Apply book search filter
        if book_filter:
            borrows = borrows.filter(
                Q(book__title__icontains=book_filter) |
                Q(book__author__icontains=book_filter) |
                Q(book__isbn__icontains=book_filter) |
                Q(book__accession_number__icontains=book_filter)
            )
            filters['book'] = book_filter
        
        # Apply date range filter
        if date_range:
            today = timezone.now().date()
            
            if date_range == 'today':
                borrows = borrows.filter(borrow_date=today)
                filters['date_range'] = 'Today'
            elif date_range == 'yesterday':
                yesterday = today - timedelta(days=1)
                borrows = borrows.filter(borrow_date=yesterday)
                filters['date_range'] = 'Yesterday'
            elif date_range == 'this_week':
                start_of_week = today - timedelta(days=today.weekday())
                borrows = borrows.filter(borrow_date__gte=start_of_week)
                filters['date_range'] = 'This Week'
            elif date_range == 'last_week':
                start_of_last_week = today - timedelta(days=today.weekday() + 7)
                end_of_last_week = start_of_last_week + timedelta(days=6)
                borrows = borrows.filter(borrow_date__range=[start_of_last_week, end_of_last_week])
                filters['date_range'] = 'Last Week'
            elif date_range == 'this_month':
                start_of_month = today.replace(day=1)
                borrows = borrows.filter(borrow_date__gte=start_of_month)
                filters['date_range'] = 'This Month'
            elif date_range == 'last_month':
                first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
                borrows = borrows.filter(borrow_date__range=[first_day_of_last_month, last_day_of_last_month])
                filters['date_range'] = 'Last Month'
            elif date_range == 'last_30_days':
                thirty_days_ago = today - timedelta(days=30)
                borrows = borrows.filter(borrow_date__gte=thirty_days_ago)
                filters['date_range'] = 'Last 30 Days'
            elif date_range == 'last_90_days':
                ninety_days_ago = today - timedelta(days=90)
                borrows = borrows.filter(borrow_date__gte=ninety_days_ago)
                filters['date_range'] = 'Last 90 Days'
            elif date_range == 'this_year':
                start_of_year = today.replace(month=1, day=1)
                borrows = borrows.filter(borrow_date__gte=start_of_year)
                filters['date_range'] = 'This Year'
        
        # Apply custom date range
        if date_from and date_to:
            try:
                from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
                to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
                borrows = borrows.filter(borrow_date__range=[from_date, to_date])
                filters['date_from'] = date_from
                filters['date_to'] = date_to
            except ValueError:
                pass
        
        # Calculate comprehensive statistics
        total_borrows = borrows.count()
        
        # Status-based counts
        active_borrows_count = borrows.filter(status='active').count()
        overdue_borrows_count = borrows.filter(status='overdue').count()
        returned_borrows_count = borrows.filter(status='returned').count()
        lost_borrows_count = borrows.filter(status='lost').count()
        cancelled_borrows_count = borrows.filter(status='cancelled').count()
        
        # Borrower type counts
        staff_borrows_count = borrows.filter(borrower_type='staff').count()
        student_borrows_count = borrows.filter(borrower_type='student').count()
        
        # Fine statistics
        total_fine_amount = borrows.aggregate(total=Sum('fine_amount'))['total'] or 0
        total_fine_paid = borrows.aggregate(total=Sum('fine_paid'))['total'] or 0
        total_fine_balance = borrows.aggregate(total=Sum('fine_balance'))['total'] or 0
        
        # Renewal statistics
        renewed_borrows_count = borrows.filter(renewed_count__gt=0).count()
        
        # Tomorrow for due soon calculation
        tomorrow = timezone.now().date() + timedelta(days=1)
        
        # Calculate overdue days for each borrow
        for borrow in borrows:
            borrow.calculate_overdue_days()
        
        # Prepare context
        context = {
            'borrows': borrows,
            'total_borrows': total_borrows,
            
            # Status statistics
            'active_borrows_count': active_borrows_count,
            'overdue_borrows_count': overdue_borrows_count,
            'returned_borrows_count': returned_borrows_count,
            'lost_borrows_count': lost_borrows_count,
            'cancelled_borrows_count': cancelled_borrows_count,
            
            # Borrower type statistics
            'staff_borrows_count': staff_borrows_count,
            'student_borrows_count': student_borrows_count,
            
            # Fine statistics
            'total_fine_amount': total_fine_amount,
            'total_fine_paid': total_fine_paid,
            'total_fine_balance': total_fine_balance,
            
            # Renewal statistics
            'renewed_borrows_count': renewed_borrows_count,
            
            # Filter information
            'filters': filters,
            
            # Dates
            'export_date': timezone.now(),
            'tomorrow': tomorrow,
            
            # Request
            'request': request,
        }
        
        # Render HTML template
        html_string = render_to_string('admin/library/reports/book_borrows_pdf.html', context)
        
        # Create PDF with WeasyPrint
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        
        # Generate filename
        filename = f'book_borrows_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating PDF report: {str(e)}')
        return redirect('admin_book_borrows_list')


@login_required
def issued_books_report_view(request):
    """Display issued books report with filtering options"""
    # Get all borrows initially
    borrows = BookBorrow.objects.select_related(
        'book', 'staff_borrower', 'student_borrower', 'book_copy', 'issued_by'
    ).prefetch_related(
        'book__category',
        'fine_payments'
    ).order_by('-borrow_date', '-created_at')
    
    # Get all available filters from request
    status_filter = request.GET.get('status', '')
    borrower_type_filter = request.GET.get('borrower_type', '')
    borrower_filter = request.GET.get('borrower', '')
    book_filter = request.GET.get('book', '')
    date_range_filter = request.GET.get('date_range', '')
    fine_status_filter = request.GET.get('fine_status', '')
    issued_by_filter = request.GET.get('issued_by', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if status_filter:
        borrows = borrows.filter(status=status_filter)
    
    if borrower_type_filter:
        if borrower_type_filter == 'staff':
            borrows = borrows.filter(borrower_type='staff')
        elif borrower_type_filter == 'student':
            borrows = borrows.filter(borrower_type='student')
    
    if borrower_filter:
        borrows = borrows.filter(
            Q(staff_borrower__admin__username__icontains=borrower_filter) |
            Q(staff_borrower__admin__first_name__icontains=borrower_filter) |
            Q(staff_borrower__admin__last_name__icontains=borrower_filter) |
            Q(student_borrower__first_name__icontains=borrower_filter) |
            Q(student_borrower__last_name__icontains=borrower_filter) |
            Q(student_borrower__registration_number__icontains=borrower_filter)
        )
    
    if book_filter:
        borrows = borrows.filter(
            Q(book__title__icontains=book_filter) |
            Q(book__author__icontains=book_filter) |
            Q(book__isbn__icontains=book_filter) |
            Q(book__accession_number__icontains=book_filter)
        )
    
    if issued_by_filter:
        borrows = borrows.filter(issued_by__username__icontains=issued_by_filter)
    
    # Apply date range filter
    if date_range_filter:
        today = timezone.now().date()
        
        if date_range_filter == 'today':
            borrows = borrows.filter(borrow_date=today)
        elif date_range_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            borrows = borrows.filter(borrow_date=yesterday)
        elif date_range_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            borrows = borrows.filter(borrow_date__gte=start_of_week)
        elif date_range_filter == 'last_week':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            borrows = borrows.filter(borrow_date__range=[start_of_last_week, end_of_last_week])
        elif date_range_filter == 'this_month':
            start_of_month = today.replace(day=1)
            borrows = borrows.filter(borrow_date__gte=start_of_month)
        elif date_range_filter == 'last_month':
            first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            borrows = borrows.filter(borrow_date__range=[first_day_of_last_month, last_day_of_last_month])
        elif date_range_filter == 'last_30_days':
            thirty_days_ago = today - timedelta(days=30)
            borrows = borrows.filter(borrow_date__gte=thirty_days_ago)
        elif date_range_filter == 'last_90_days':
            ninety_days_ago = today - timedelta(days=90)
            borrows = borrows.filter(borrow_date__gte=ninety_days_ago)
        elif date_range_filter == 'this_year':
            start_of_year = today.replace(month=1, day=1)
            borrows = borrows.filter(borrow_date__gte=start_of_year)
    
    # Apply custom date range
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            borrows = borrows.filter(borrow_date__range=[from_date, to_date])
        except ValueError:
            pass
    
    # Apply fine status filter
    if fine_status_filter:
        if fine_status_filter == 'with_fine':
            borrows = borrows.filter(fine_amount__gt=0)
        elif fine_status_filter == 'no_fine':
            borrows = borrows.filter(fine_amount=0)
        elif fine_status_filter == 'paid':
            borrows = borrows.filter(fine_balance=0, fine_amount__gt=0)
        elif fine_status_filter == 'partial':
            borrows = borrows.filter(fine_balance__gt=0, fine_balance__lt=F('fine_amount'))
    
    # Calculate statistics
    total_active = borrows.filter(status='active').count()
    total_overdue = borrows.filter(status='overdue').count()
    total_returned = borrows.filter(status='returned').count()
    total_staff = borrows.filter(borrower_type='staff').count()
    total_student = borrows.filter(borrower_type='student').count()
    
    total_fine = borrows.aggregate(total=Sum('fine_amount'))['total'] or 0
    total_fine_paid = borrows.aggregate(total=Sum('fine_paid'))['total'] or 0
    total_fine_balance = borrows.aggregate(total=Sum('fine_balance'))['total'] or 0
    
    # Get unique values for filters
    status_choices = BookBorrow.BORROW_STATUS_CHOICES
    unique_books = Book.objects.filter(
        id__in=borrows.values_list('book_id', flat=True).distinct()
    ).values('id', 'title').order_by('title')[:50]
    
    unique_issuers = Staffs.objects.filter(
        id__in=borrows.values_list('issued_by_id', flat=True).distinct()
    ).select_related('admin').order_by('admin__username')
    
    context = {
        'borrows': borrows,
        
        # Statistics
        'total_active': total_active,
        'total_overdue': total_overdue,
        'total_returned': total_returned,
        'total_staff': total_staff,
        'total_student': total_student,
        'total_fine': total_fine,
        'total_fine_paid': total_fine_paid,
        'total_fine_balance': total_fine_balance,
        
        # Filter options
        'status_choices': status_choices,
        'unique_books': unique_books,
        'unique_issuers': unique_issuers,
        
        # Current filter values
        'status_filter': status_filter,
        'borrower_type_filter': borrower_type_filter,
        'borrower_filter': borrower_filter,
        'book_filter': book_filter,
        'date_range_filter': date_range_filter,
        'fine_status_filter': fine_status_filter,
        'issued_by_filter': issued_by_filter,
        'date_from': date_from,
        'date_to': date_to,
        
        # Filter options for dropdowns
        'date_range_options': [
            ('', 'All Time'),
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('last_30_days', 'Last 30 Days'),
            ('last_90_days', 'Last 90 Days'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        
        'fine_status_options': [
            ('', 'All'),
            ('with_fine', 'With Fine'),
            ('no_fine', 'No Fine'),
            ('paid', 'Fully Paid'),
            ('partial', 'Partially Paid'),
        ],
        
        'borrower_type_options': [
            ('', 'All Types'),
            ('staff', 'Staff'),
            ('student', 'Student'),
        ],
    }
    
    return render(request, 'admin/library/reports/issued_books_report.html', context)


@login_required
def export_issued_books_pdf(request):
    """Export issued books report to PDF"""
    # Get all borrows with filters
    borrows = BookBorrow.objects.select_related(
        'book', 'staff_borrower', 'student_borrower', 'book_copy', 'issued_by'
    ).order_by('-borrow_date', '-created_at')
    
    # Apply filters from request
    filters = {}
    
    status_filter = request.GET.get('status', '')
    borrower_type_filter = request.GET.get('borrower_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if status_filter:
        borrows = borrows.filter(status=status_filter)
        filters['status'] = status_filter
    
    if borrower_type_filter:
        borrows = borrows.filter(borrower_type=borrower_type_filter)
        filters['borrower_type'] = borrower_type_filter
    
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            borrows = borrows.filter(borrow_date__range=[from_date, to_date])
            filters['date_from'] = date_from
            filters['date_to'] = date_to
        except ValueError:
            pass
    
    # Calculate statistics
    total_active = borrows.filter(status='active').count()
    total_overdue = borrows.filter(status='overdue').count()
    total_returned = borrows.filter(status='returned').count()
    total_staff = borrows.filter(borrower_type='staff').count()
    total_student = borrows.filter(borrower_type='student').count()
    
    total_fine = borrows.aggregate(total=Sum('fine_amount'))['total'] or 0
    total_fine_paid = borrows.aggregate(total=Sum('fine_paid'))['total'] or 0
    total_fine_balance = borrows.aggregate(total=Sum('fine_balance'))['total'] or 0
    
    # Prepare context for PDF template
    context = {
        'borrows': borrows,
        'export_date': timezone.now(),
        'filters': filters,
        'total_active': total_active,
        'total_overdue': total_overdue,
        'total_returned': total_returned,
        'total_staff': total_staff,
        'total_student': total_student,
        'total_fine': total_fine,
        'total_fine_paid': total_fine_paid,
        'total_fine_balance': total_fine_balance,
        'request': request,  # Pass request object for user info
    }
    
    # Render HTML template
    html_string = render_to_string('admin/library/reports/issued_books_pdf.html', context)
    
    # Create PDF
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f'issued_books_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def returned_books_report_view(request):
    """Display returned books report with filtering options"""
    # Get all returned books
    returns = BookReturn.objects.select_related(
        'borrow',
        'borrow__book',
        'borrow__staff_borrower__admin',
        'borrow__student_borrower',
        'borrow__book_copy'
    ).order_by('-return_date', '-created_at')
    
    # Get all available filters from request
    borrower_type_filter = request.GET.get('borrower_type', '')
    fine_status_filter = request.GET.get('fine_status', '')
    return_condition_filter = request.GET.get('return_condition', '')
    date_range_filter = request.GET.get('date_range', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if borrower_type_filter:
        returns = returns.filter(borrow__borrower_type=borrower_type_filter)
    
    if return_condition_filter:
        returns = returns.filter(condition=return_condition_filter)
    
    # Apply date range filter
    if date_range_filter:
        today = timezone.now().date()
        
        if date_range_filter == 'today':
            returns = returns.filter(return_date=today)
        elif date_range_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            returns = returns.filter(return_date=yesterday)
        elif date_range_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            returns = returns.filter(return_date__gte=start_of_week)
        elif date_range_filter == 'last_week':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            returns = returns.filter(return_date__range=[start_of_last_week, end_of_last_week])
        elif date_range_filter == 'this_month':
            start_of_month = today.replace(day=1)
            returns = returns.filter(return_date__gte=start_of_month)
        elif date_range_filter == 'last_month':
            first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            returns = returns.filter(return_date__range=[first_day_of_last_month, last_day_of_last_month])
        elif date_range_filter == 'last_30_days':
            thirty_days_ago = today - timedelta(days=30)
            returns = returns.filter(return_date__gte=thirty_days_ago)
        elif date_range_filter == 'last_90_days':
            ninety_days_ago = today - timedelta(days=90)
            returns = returns.filter(return_date__gte=ninety_days_ago)
        elif date_range_filter == 'this_year':
            start_of_year = today.replace(month=1, day=1)
            returns = returns.filter(return_date__gte=start_of_year)
    
    # Apply custom date range
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            returns = returns.filter(return_date__range=[from_date, to_date])
        except ValueError:
            pass
    
    # Calculate statistics
    total_returns = returns.count()
    
    # Calculate late returns
    late_returns = 0
    on_time_returns = 0
    total_late_days = 0
    
    for return_item in returns:
        borrow = return_item.borrow
        if borrow.actual_return_date and borrow.actual_return_date > borrow.due_date:
            late_returns += 1
            total_late_days += (borrow.actual_return_date - borrow.due_date).days
        else:
            on_time_returns += 1
    
    avg_late_days = total_late_days / late_returns if late_returns > 0 else 0
    
    # Borrower type counts
    staff_returns = returns.filter(borrow__borrower_type='staff').count()
    student_returns = returns.filter(borrow__borrower_type='student').count()
    
    # Condition counts
    damaged_books = returns.filter(condition='damaged').count()
    good_condition_returns = returns.filter(condition='good').count()
    
    # Condition distribution
    condition_distribution = []
    condition_counts = returns.values('condition').annotate(count=Count('condition'))
    for item in condition_counts:
        condition_distribution.append({
            'code': item['condition'],
            'name': dict(BookReturn._meta.get_field('condition').choices).get(item['condition'], item['condition']),
            'count': item['count'],
            'percentage': (item['count'] / total_returns * 100) if total_returns > 0 else 0
        })
    
    # Financial statistics
    total_fine_charged = sum(float(r.borrow.fine_amount) for r in returns)
    total_fine_collected = sum(float(r.borrow.fine_paid) for r in returns)
    total_fine_collected_at_return = sum(float(r.fine_collected) for r in returns)
    total_fine_outstanding = total_fine_charged - total_fine_collected
    
    collection_rate = (total_fine_collected / total_fine_charged * 100) if total_fine_charged > 0 else 0
    
    # Calculate late days for each return for display
    returns_with_late_days = []
    for return_item in returns:
        borrow = return_item.borrow
        late_days = 0
        if borrow.actual_return_date and borrow.actual_return_date > borrow.due_date:
            late_days = (borrow.actual_return_date - borrow.due_date).days
        
        # Create a copy of return with late_days attribute
        return_item.late_days = late_days
        returns_with_late_days.append(return_item)
    
    context = {
        'returns': returns_with_late_days,
        'total_returns': total_returns,
        
        # Timeline statistics
        'late_returns': late_returns,
        'on_time_returns': on_time_returns,
        'avg_late_days': avg_late_days,
        'total_late_days': total_late_days,
        
        # Borrower statistics
        'staff_returns': staff_returns,
        'student_returns': student_returns,
        
        # Condition statistics
        'damaged_books': damaged_books,
        'good_condition_returns': good_condition_returns,
        'condition_distribution': condition_distribution,
        
        # Financial statistics
        'total_fine_charged': total_fine_charged,
        'total_fine_collected': total_fine_collected,
        'total_fine_collected_at_return': total_fine_collected_at_return,
        'total_fine_outstanding': total_fine_outstanding,
        'collection_rate': collection_rate,
        
        # Current filter values
        'borrower_type_filter': borrower_type_filter,
        'fine_status_filter': fine_status_filter,
        'return_condition_filter': return_condition_filter,
        'date_range_filter': date_range_filter,
        'date_from': date_from,
        'date_to': date_to,
        
        # Filter options
        'condition_choices': BookReturn._meta.get_field('condition').choices,
        
        # Filter options for dropdowns
        'date_range_options': [
            ('', 'All Time'),
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('last_30_days', 'Last 30 Days'),
            ('last_90_days', 'Last 90 Days'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        
        'fine_status_options': [
            ('', 'All'),
            ('with_fine', 'With Fine'),
            ('no_fine', 'No Fine'),
            ('paid', 'Fully Paid'),
            ('partial', 'Partially Paid'),
        ],
        
        'borrower_type_options': [
            ('', 'All Types'),
            ('staff', 'Staff'),
            ('student', 'Student'),
        ],
    }
    
    return render(request, 'admin/library/reports/returned_books_report.html', context)


@login_required
def export_returned_books_pdf(request):
    """Export returned books report to PDF using WeasyPrint"""
    # Get all returned books with filters
    returns = BookReturn.objects.select_related(
        'borrow',
        'borrow__book',
        'borrow__staff_borrower__admin',
        'borrow__student_borrower',
        'borrow__book_copy'
    ).order_by('-return_date', '-created_at')
    
    # Apply filters from request
    filters = {}
    
    borrower_type_filter = request.GET.get('borrower_type', '')
    return_condition_filter = request.GET.get('return_condition', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if borrower_type_filter:
        returns = returns.filter(borrow__borrower_type=borrower_type_filter)
        filters['borrower_type'] = borrower_type_filter
    
    if return_condition_filter:
        returns = returns.filter(condition=return_condition_filter)
        filters['return_condition'] = return_condition_filter
    
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            returns = returns.filter(return_date__range=[from_date, to_date])
            filters['date_from'] = date_from
            filters['date_to'] = date_to
        except ValueError:
            pass
    
    # Calculate statistics for PDF
    total_returns = returns.count()
    
    # Calculate late returns
    late_returns = 0
    on_time_returns = 0
    total_late_days = 0
    
    for return_item in returns:
        borrow = return_item.borrow
        if borrow.actual_return_date and borrow.actual_return_date > borrow.due_date:
            late_returns += 1
            total_late_days += (borrow.actual_return_date - borrow.due_date).days
        else:
            on_time_returns += 1
    
    avg_late_days = total_late_days / late_returns if late_returns > 0 else 0
    
    # Borrower type counts
    staff_returns = returns.filter(borrow__borrower_type='staff').count()
    student_returns = returns.filter(borrow__borrower_type='student').count()
    
    # Condition counts
    damaged_books = returns.filter(condition='damaged').count()
    good_condition_returns = returns.filter(condition='good').count()
    
    # Condition distribution
    condition_distribution = []
    condition_counts = returns.values('condition').annotate(count=Count('condition'))
    for item in condition_counts:
        condition_distribution.append({
            'name': dict(BookReturn._meta.get_field('condition').choices).get(item['condition'], item['condition']),
            'count': item['count'],
            'percentage': (item['count'] / total_returns * 100) if total_returns > 0 else 0
        })
    
    # Financial statistics
    total_fine_charged = sum(float(r.borrow.fine_amount) for r in returns)
    total_fine_collected = sum(float(r.borrow.fine_paid) for r in returns)
    total_fine_outstanding = total_fine_charged - total_fine_collected
    collection_rate = (total_fine_collected / total_fine_charged * 100) if total_fine_charged > 0 else 0
    
    # Add late_days to each return for display
    returns_with_late_days = []
    for return_item in returns:
        borrow = return_item.borrow
        late_days = 0
        if borrow.actual_return_date and borrow.actual_return_date > borrow.due_date:
            late_days = (borrow.actual_return_date - borrow.due_date).days
        return_item.late_days = late_days
        returns_with_late_days.append(return_item)
    
    # Prepare context for PDF template
    context = {
        'returns': returns_with_late_days,
        'export_date': timezone.now(),
        'filters': filters,
        
        # Statistics
        'total_returns': total_returns,
        'late_returns': late_returns,
        'on_time_returns': on_time_returns,
        'avg_late_days': avg_late_days,
        'staff_returns': staff_returns,
        'student_returns': student_returns,
        'damaged_books': damaged_books,
        'good_condition_returns': good_condition_returns,
        'total_fine_charged': total_fine_charged,
        'total_fine_collected': total_fine_collected,
        'total_fine_outstanding': total_fine_outstanding,
        'collection_rate': collection_rate,
        'condition_distribution': condition_distribution,
        
        'request': request,  # Pass request object for user info
    }
    
    # Render HTML template
    html_string = render_to_string('admin/library/reports/returned_books_pdf.html', context)
    
    # Create PDF using WeasyPrint
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f'returned_books_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def overdue_books_report_view(request):
    """Display overdue books report with filtering options"""
    # Get all overdue books (status='overdue' or due_date passed with status='active')
    from django.db.models import Q
    from datetime import date
    
    today = timezone.now().date()
    
    # Get overdue books (status='overdue' or due_date < today with status='active')
    overdue_books_qs = BookBorrow.objects.filter(
        Q(status='overdue') | Q(status='active', due_date__lt=today)
    ).select_related(
        'book',
        'staff_borrower__admin',
        'student_borrower',
        'book_copy'
    ).order_by('-due_date', '-created_at')
    
    # Get all available filters from request
    borrower_type_filter = request.GET.get('borrower_type', '')
    overdue_days_filter = request.GET.get('overdue_days', '')
    fine_status_filter = request.GET.get('fine_status', '')
    date_range_filter = request.GET.get('date_range', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if borrower_type_filter:
        overdue_books_qs = overdue_books_qs.filter(borrower_type=borrower_type_filter)
    
    # Apply overdue days filter
    if overdue_days_filter:
        today = timezone.now().date()
        if overdue_days_filter == '1-7':
            week_ago = today - timedelta(days=7)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[week_ago, today])
        elif overdue_days_filter == '8-14':
            two_weeks_ago = today - timedelta(days=14)
            week_ago = today - timedelta(days=7)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[two_weeks_ago, week_ago])
        elif overdue_days_filter == '15-30':
            month_ago = today - timedelta(days=30)
            two_weeks_ago = today - timedelta(days=14)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[month_ago, two_weeks_ago])
        elif overdue_days_filter == '31-90':
            three_months_ago = today - timedelta(days=90)
            month_ago = today - timedelta(days=30)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[three_months_ago, month_ago])
        elif overdue_days_filter == '90+':
            three_months_ago = today - timedelta(days=90)
            overdue_books_qs = overdue_books_qs.filter(due_date__lt=three_months_ago)
    
    # Apply due date range filter
    if date_range_filter:
        today = timezone.now().date()
        
        if date_range_filter == 'today':
            overdue_books_qs = overdue_books_qs.filter(due_date=today)
        elif date_range_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            overdue_books_qs = overdue_books_qs.filter(due_date=yesterday)
        elif date_range_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            overdue_books_qs = overdue_books_qs.filter(due_date__gte=start_of_week)
        elif date_range_filter == 'last_week':
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[start_of_last_week, end_of_last_week])
        elif date_range_filter == 'this_month':
            start_of_month = today.replace(day=1)
            overdue_books_qs = overdue_books_qs.filter(due_date__gte=start_of_month)
        elif date_range_filter == 'last_month':
            first_day_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[first_day_of_last_month, last_day_of_last_month])
        elif date_range_filter == 'last_30_days':
            thirty_days_ago = today - timedelta(days=30)
            overdue_books_qs = overdue_books_qs.filter(due_date__gte=thirty_days_ago)
        elif date_range_filter == 'last_90_days':
            ninety_days_ago = today - timedelta(days=90)
            overdue_books_qs = overdue_books_qs.filter(due_date__gte=ninety_days_ago)
        elif date_range_filter == 'this_year':
            start_of_year = today.replace(month=1, day=1)
            overdue_books_qs = overdue_books_qs.filter(due_date__gte=start_of_year)
    
    # Apply custom date range
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[from_date, to_date])
        except ValueError:
            pass
    
    # Calculate overdue days and severity for each book
    overdue_books = []
    total_overdue_days = 0
    
    for borrow in overdue_books_qs:
        # Calculate overdue days
        overdue_days = borrow.calculate_overdue_days()
        
        # Calculate fine amount if not already calculated
        if borrow.fine_amount == 0:
            borrow.update_fine()
        
        # Determine overdue severity
        if overdue_days > 90:
            overdue_severity = 'critical'
        elif overdue_days >= 31:
            overdue_severity = 'high'
        elif overdue_days >= 15:
            overdue_severity = 'medium'
        else:
            overdue_severity = 'low'
        
        # Get fine per day from book
        fine_per_day = borrow.book.fine_amount if borrow.book else Decimal('500.00')
        
        # Add attributes to borrow object for template
        borrow.overdue_days = overdue_days
        borrow.overdue_severity = overdue_severity
        borrow.fine_per_day = fine_per_day
        
        # Add to list
        overdue_books.append(borrow)
        total_overdue_days += overdue_days
    
    # Calculate statistics
    total_overdue = len(overdue_books)
    
    # Severity counts
    critical_count = len([b for b in overdue_books if b.overdue_severity == 'critical'])
    high_count = len([b for b in overdue_books if b.overdue_severity == 'high'])
    medium_count = len([b for b in overdue_books if b.overdue_severity == 'medium'])
    low_count = len([b for b in overdue_books if b.overdue_severity == 'low'])
    
    # Percentage calculations
    critical_percentage = (critical_count / total_overdue * 100) if total_overdue > 0 else 0
    high_percentage = (high_count / total_overdue * 100) if total_overdue > 0 else 0
    medium_percentage = (medium_count / total_overdue * 100) if total_overdue > 0 else 0
    low_percentage = (low_count / total_overdue * 100) if total_overdue > 0 else 0
    
    # Borrower type counts
    staff_overdue = len([b for b in overdue_books if b.borrower_type == 'staff'])
    student_overdue = len([b for b in overdue_books if b.borrower_type == 'student'])
    
    staff_percentage = (staff_overdue / total_overdue * 100) if total_overdue > 0 else 0
    student_percentage = (student_overdue / total_overdue * 100) if total_overdue > 0 else 0
    
    # Financial statistics
    total_fine = sum(float(b.fine_amount) for b in overdue_books)
    total_fine_paid = sum(float(b.fine_paid) for b in overdue_books)
    total_unpaid_fine = total_fine - total_fine_paid
    
    avg_overdue_days = total_overdue_days / total_overdue if total_overdue > 0 else 0
    collection_rate = (total_fine_paid / total_fine * 100) if total_fine > 0 else 0
    
    # Prepare severity display mapping
    severity_display = {
        'critical': 'Critical (>90 days)',
        'high': 'High (31-90 days)',
        'medium': 'Medium (15-30 days)',
        'low': 'Low (1-14 days)',
    }
    
    # Add display methods to borrow objects
    for borrow in overdue_books:
        borrow.get_overdue_severity_display = lambda s=borrow.overdue_severity: severity_display.get(s, s)
    
    context = {
        'overdue_books': overdue_books,
        'total_overdue': total_overdue,
        
        # Severity statistics
        'critical_count': critical_count,
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'critical_percentage': critical_percentage,
        'high_percentage': high_percentage,
        'medium_percentage': medium_percentage,
        'low_percentage': low_percentage,
        
        # Borrower statistics
        'staff_overdue': staff_overdue,
        'student_overdue': student_overdue,
        'staff_percentage': staff_percentage,
        'student_percentage': student_percentage,
        
        # Financial statistics
        'total_fine': total_fine,
        'total_fine_paid': total_fine_paid,
        'total_unpaid_fine': total_unpaid_fine,
        'avg_overdue_days': avg_overdue_days,
        'collection_rate': collection_rate,
        
        # Current filter values
        'borrower_type_filter': borrower_type_filter,
        'overdue_days_filter': overdue_days_filter,
        'fine_status_filter': fine_status_filter,
        'date_range_filter': date_range_filter,
        'date_from': date_from,
        'date_to': date_to,
        
        # Filter options for dropdowns
        'date_range_options': [
            ('', 'All Time'),
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('last_30_days', 'Last 30 Days'),
            ('last_90_days', 'Last 90 Days'),
            ('this_year', 'This Year'),
            ('custom', 'Custom Range'),
        ],
        
        'fine_status_options': [
            ('', 'All'),
            ('unpaid', 'Unpaid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Fully Paid'),
        ],
        
        'overdue_days_options': [
            ('', 'All'),
            ('1-7', '1-7 days'),
            ('8-14', '8-14 days'),
            ('15-30', '15-30 days'),
            ('31-90', '31-90 days'),
            ('90+', '90+ days'),
        ],
        
        'borrower_type_options': [
            ('', 'All Types'),
            ('staff', 'Staff'),
            ('student', 'Student'),
        ],
        
        'severity_display': severity_display,
    }
    
    return render(request, 'admin/library/reports/overdue_books_report.html', context)


@login_required
def export_overdue_books_pdf(request):
    """Export overdue books report to PDF using WeasyPrint"""
    # Get all overdue books
    from django.db.models import Q
    from datetime import date
    
    today = timezone.now().date()
    
    overdue_books_qs = BookBorrow.objects.filter(
        Q(status='overdue') | Q(status='active', due_date__lt=today)
    ).select_related(
        'book',
        'staff_borrower__admin',
        'student_borrower',
        'book_copy'
    ).order_by('-due_date', '-created_at')
    
    # Apply filters from request
    filters = {}
    
    borrower_type_filter = request.GET.get('borrower_type', '')
    overdue_days_filter = request.GET.get('overdue_days', '')
    fine_status_filter = request.GET.get('fine_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if borrower_type_filter:
        overdue_books_qs = overdue_books_qs.filter(borrower_type=borrower_type_filter)
        filters['borrower_type'] = borrower_type_filter
    
    if overdue_days_filter:
        filters['overdue_days'] = overdue_days_filter
        today = timezone.now().date()
        if overdue_days_filter == '1-7':
            week_ago = today - timedelta(days=7)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[week_ago, today])
        elif overdue_days_filter == '8-14':
            two_weeks_ago = today - timedelta(days=14)
            week_ago = today - timedelta(days=7)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[two_weeks_ago, week_ago])
        elif overdue_days_filter == '15-30':
            month_ago = today - timedelta(days=30)
            two_weeks_ago = today - timedelta(days=14)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[month_ago, two_weeks_ago])
        elif overdue_days_filter == '31-90':
            three_months_ago = today - timedelta(days=90)
            month_ago = today - timedelta(days=30)
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[three_months_ago, month_ago])
        elif overdue_days_filter == '90+':
            three_months_ago = today - timedelta(days=90)
            overdue_books_qs = overdue_books_qs.filter(due_date__lt=three_months_ago)
    
    if fine_status_filter:
        filters['fine_status'] = fine_status_filter
        if fine_status_filter == 'unpaid':
            overdue_books_qs = overdue_books_qs.filter(fine_balance__gt=0)
        elif fine_status_filter == 'partial':
            overdue_books_qs = overdue_books_qs.filter(fine_paid__gt=0, fine_balance__gt=0)
        elif fine_status_filter == 'paid':
            overdue_books_qs = overdue_books_qs.filter(fine_balance=0, fine_amount__gt=0)
    
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            overdue_books_qs = overdue_books_qs.filter(due_date__range=[from_date, to_date])
            filters['date_from'] = date_from
            filters['date_to'] = date_to
        except ValueError:
            pass
    
    # Calculate overdue days and severity for each book
    overdue_books = []
    total_overdue_days = 0
    all_fines = []
    
    for borrow in overdue_books_qs:
        # Calculate overdue days
        overdue_days = borrow.calculate_overdue_days()
        
        # Calculate fine amount if not already calculated
        if borrow.fine_amount == 0:
            borrow.update_fine()
        
        # Determine overdue severity
        if overdue_days > 90:
            overdue_severity = 'critical'
        elif overdue_days >= 31:
            overdue_severity = 'high'
        elif overdue_days >= 15:
            overdue_severity = 'medium'
        else:
            overdue_severity = 'low'
        
        # Get fine per day from book
        fine_per_day = borrow.book.fine_amount if borrow.book else Decimal('500.00')
        
        # Add attributes to borrow object for template
        borrow.overdue_days = overdue_days
        borrow.overdue_severity = overdue_severity
        borrow.fine_per_day = fine_per_day
        borrow.get_overdue_severity_display = lambda s=overdue_severity: {
            'critical': 'Critical (>90 days)',
            'high': 'High (31-90 days)',
            'medium': 'Medium (15-30 days)',
            'low': 'Low (1-14 days)',
        }.get(s, s)
        
        # Add to lists
        overdue_books.append(borrow)
        total_overdue_days += overdue_days
        all_fines.append({
            'borrow': borrow,
            'fine_amount': borrow.fine_amount,
            'fine_balance': borrow.fine_balance,
        })
    
    # Calculate statistics
    total_overdue = len(overdue_books)
    
    # Severity counts
    critical_count = len([b for b in overdue_books if b.overdue_severity == 'critical'])
    high_count = len([b for b in overdue_books if b.overdue_severity == 'high'])
    medium_count = len([b for b in overdue_books if b.overdue_severity == 'medium'])
    low_count = len([b for b in overdue_books if b.overdue_severity == 'low'])
    
    # Percentage calculations
    critical_percentage = (critical_count / total_overdue * 100) if total_overdue > 0 else 0
    high_percentage = (high_count / total_overdue * 100) if total_overdue > 0 else 0
    medium_percentage = (medium_count / total_overdue * 100) if total_overdue > 0 else 0
    low_percentage = (low_count / total_overdue * 100) if total_overdue > 0 else 0
    
    # Borrower type counts
    staff_overdue = len([b for b in overdue_books if b.borrower_type == 'staff'])
    student_overdue = len([b for b in overdue_books if b.borrower_type == 'student'])
    
    staff_percentage = (staff_overdue / total_overdue * 100) if total_overdue > 0 else 0
    student_percentage = (student_overdue / total_overdue * 100) if total_overdue > 0 else 0
    
    # Financial statistics
    total_fine = sum(float(b.fine_amount) for b in overdue_books)
    total_fine_paid = sum(float(b.fine_paid) for b in overdue_books)
    total_unpaid_fine = total_fine - total_fine_paid
    
    avg_overdue_days = total_overdue_days / total_overdue if total_overdue > 0 else 0
    collection_rate = (total_fine_paid / total_fine * 100) if total_fine > 0 else 0
    
    # Get top longest overdue
    top_longest_overdue = sorted(overdue_books, key=lambda x: x.overdue_days, reverse=True)[:10]
    
    # Get top highest fines
    top_highest_fines = sorted(overdue_books, key=lambda x: x.fine_amount, reverse=True)[:10]
    
    # Prepare context for PDF template
    context = {
        'overdue_books': overdue_books,
        'export_date': timezone.now(),
        'filters': filters,
        
        # Statistics
        'total_overdue': total_overdue,
        'critical_count': critical_count,
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'critical_percentage': critical_percentage,
        'high_percentage': high_percentage,
        'medium_percentage': medium_percentage,
        'low_percentage': low_percentage,
        'staff_overdue': staff_overdue,
        'student_overdue': student_overdue,
        'staff_percentage': staff_percentage,
        'student_percentage': student_percentage,
        'total_fine': total_fine,
        'total_fine_paid': total_fine_paid,
        'total_unpaid_fine': total_unpaid_fine,
        'avg_overdue_days': avg_overdue_days,
        'collection_rate': collection_rate,
        
        # Top lists for analysis
        'top_longest_overdue': top_longest_overdue,
        'top_highest_fines': top_highest_fines,
        
        'request': request,  # Pass request object for user info
    }
    
    # Render HTML template
    html_string = render_to_string('admin/library/reports/overdue_books_pdf.html', context)
    
    # Create PDF using WeasyPrint
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f'overdue_books_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response