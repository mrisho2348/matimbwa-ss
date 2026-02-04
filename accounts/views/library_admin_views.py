from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from library.models import BookCategory, Book, BookBorrow


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
