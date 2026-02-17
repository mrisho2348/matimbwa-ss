# ============================================================================
# HOSTEL MANAGEMENT VIEWS
# ============================================================================

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Count, Q

from core.models import AcademicYear
from students.models import Bed, Hostel, HostelRoom, Student, StudentHostelAllocation


@login_required
def hostels_list(request):
    """
    Display hostels management page
    """
    hostels = Hostel.objects.all().order_by('name')
    
    # Get statistics
    total_hostels = hostels.count()
    active_hostels = hostels.filter(is_active=True).count()
    boys_hostels = hostels.filter(hostel_type='boys').count()
    girls_hostels = hostels.filter(hostel_type='girls').count()
    mixed_hostels = hostels.filter(hostel_type='mixed').count()
    
    # Calculate total capacity
    total_capacity = hostels.aggregate(total=models.Sum('max_students'))['total'] or 0
    
    # Get allocation counts (if you have allocations)
    # This will need to be updated based on your allocation model
    allocated_count = 0  # Placeholder
    
    context = {
        'hostels': hostels,
        'total_hostels': total_hostels,
        'active_hostels': active_hostels,
        'boys_hostels': boys_hostels,
        'girls_hostels': girls_hostels,
        'mixed_hostels': mixed_hostels,
        'total_capacity': total_capacity,
        'allocated_count': allocated_count,
        'hostel_types': Hostel.HOSTEL_TYPES,
        'payment_modes': Hostel.PAYMENT_MODE,
        'page_title': 'Hostel Management',
    }
    
    return render(request, 'admin/hostels/hostels_list.html', context)


@login_required
def hostels_crud(request):
    """
    Handle AJAX CRUD operations for hostels
    """
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_hostel(request)
            elif action == 'update':
                return update_hostel(request)
            elif action == 'toggle_status':
                return toggle_hostel_status(request)
            elif action == 'delete':
                return delete_hostel(request)
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


def create_hostel(request):
    """Create a new hostel"""
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    hostel_type = request.POST.get('hostel_type', '').strip()
    max_students_str = request.POST.get('max_students', '').strip()
    total_fee_str = request.POST.get('total_fee', '').strip()
    payment_mode = request.POST.get('payment_mode', '').strip()
    installments_count_str = request.POST.get('installments_count', '1').strip()
    
    # Validate required fields
    required_fields = {
        'name': name,
        'code': code,
        'hostel_type': hostel_type,
        'max_students': max_students_str,
        'total_fee': total_fee_str,
        'payment_mode': payment_mode
    }
    
    for field_name, value in required_fields.items():
        if not value:
            return JsonResponse({
                'success': False,
                'message': f'{field_name.replace("_", " ").title()} is required.'
            })
    
    # Validate name and code
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Hostel name must be at least 2 characters long.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Hostel name cannot exceed 100 characters.'
        })
    
    if len(code) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Hostel code must be at least 2 characters long.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Hostel code cannot exceed 20 characters.'
        })
    
    # Validate code format (alphanumeric with optional underscore)
    if not code.replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Hostel code can only contain letters, numbers, and underscores.'
        })
    
    # Validate max_students
    try:
        max_students = int(max_students_str)
        if max_students < 1:
            return JsonResponse({
                'success': False,
                'message': 'Maximum students must be at least 1.'
            })
        if max_students > 1000:
            return JsonResponse({
                'success': False,
                'message': 'Maximum students cannot exceed 1000.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Maximum students must be a valid number.'
        })
    
    # Validate total_fee
    try:
        total_fee = float(total_fee_str)
        if total_fee < 0:
            return JsonResponse({
                'success': False,
                'message': 'Total fee cannot be negative.'
            })
        if total_fee > 9999999.99:
            return JsonResponse({
                'success': False,
                'message': 'Total fee is too high.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Total fee must be a valid number.'
        })
    
    # Validate hostel_type
    valid_types = [choice[0] for choice in Hostel.HOSTEL_TYPES]
    if hostel_type not in valid_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid hostel type selected.'
        })
    
    # Validate payment_mode
    valid_modes = [choice[0] for choice in Hostel.PAYMENT_MODE]
    if payment_mode not in valid_modes:
        return JsonResponse({
            'success': False,
            'message': 'Invalid payment mode selected.'
        })
    
    # Validate installments_count
    try:
        installments_count = int(installments_count_str)
        if payment_mode == 'installments':
            if installments_count < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Installments count must be at least 1.'
                })
            if installments_count > 12:
                return JsonResponse({
                    'success': False,
                    'message': 'Installments count cannot exceed 12.'
                })
        else:
            installments_count = 1  # Set to default if not installments
    except ValueError:
        installments_count = 1
    
    # Check for duplicate name
    if Hostel.objects.filter(name__iexact=name).exists():
        return JsonResponse({
            'success': False,
            'message': f'A hostel with name "{name}" already exists.'
        })
    
    # Check for duplicate code
    if Hostel.objects.filter(code__iexact=code).exists():
        return JsonResponse({
            'success': False,
            'message': f'A hostel with code "{code}" already exists.'
        })
    
    # Get optional field
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Create the hostel
        hostel = Hostel.objects.create(
            name=name,
            code=code,
            hostel_type=hostel_type,
            max_students=max_students,
            total_fee=total_fee,
            payment_mode=payment_mode,
            installments_count=installments_count,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Hostel "{name}" created successfully.',
            'hostel': {
                'id': hostel.id,
                'name': hostel.name,
                'code': hostel.code,
                'hostel_type': hostel.hostel_type,
                'hostel_type_display': hostel.get_hostel_type_display(),
                'max_students': hostel.max_students,
                'total_fee': float(hostel.total_fee),
                'payment_mode': hostel.payment_mode,
                'payment_mode_display': hostel.get_payment_mode_display(),
                'installments_count': hostel.installments_count,
                'is_active': hostel.is_active,
                'created_at': hostel.created_at.strftime('%Y-%m-%d')
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A hostel with this name or code already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating hostel: {str(e)}'
        })


def update_hostel(request):
    """Update an existing hostel"""
    hostel_id = request.POST.get('id')
    if not hostel_id:
        return JsonResponse({
            'success': False,
            'message': 'Hostel ID is required.'
        })
    
    try:
        hostel = Hostel.objects.get(id=hostel_id)
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Hostel not found.'
        })
    
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    hostel_type = request.POST.get('hostel_type', '').strip()
    max_students_str = request.POST.get('max_students', '').strip()
    total_fee_str = request.POST.get('total_fee', '').strip()
    payment_mode = request.POST.get('payment_mode', '').strip()
    installments_count_str = request.POST.get('installments_count', '1').strip()
    
    # Validate required fields
    required_fields = {
        'name': name,
        'code': code,
        'hostel_type': hostel_type,
        'max_students': max_students_str,
        'total_fee': total_fee_str,
        'payment_mode': payment_mode
    }
    
    for field_name, value in required_fields.items():
        if not value:
            return JsonResponse({
                'success': False,
                'message': f'{field_name.replace("_", " ").title()} is required.'
            })
    
    # Validate name and code
    if len(name) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Hostel name must be at least 2 characters long.'
        })
    
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Hostel name cannot exceed 100 characters.'
        })
    
    if len(code) < 2:
        return JsonResponse({
            'success': False,
            'message': 'Hostel code must be at least 2 characters long.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Hostel code cannot exceed 20 characters.'
        })
    
    # Validate code format
    if not code.replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Hostel code can only contain letters, numbers, and underscores.'
        })
    
    # Validate max_students
    try:
        max_students = int(max_students_str)
        if max_students < 1:
            return JsonResponse({
                'success': False,
                'message': 'Maximum students must be at least 1.'
            })
        if max_students > 1000:
            return JsonResponse({
                'success': False,
                'message': 'Maximum students cannot exceed 1000.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Maximum students must be a valid number.'
        })
    
    # Validate total_fee
    try:
        total_fee = float(total_fee_str)
        if total_fee < 0:
            return JsonResponse({
                'success': False,
                'message': 'Total fee cannot be negative.'
            })
        if total_fee > 9999999.99:
            return JsonResponse({
                'success': False,
                'message': 'Total fee is too high.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Total fee must be a valid number.'
        })
    
    # Validate hostel_type
    valid_types = [choice[0] for choice in Hostel.HOSTEL_TYPES]
    if hostel_type not in valid_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid hostel type selected.'
        })
    
    # Validate payment_mode
    valid_modes = [choice[0] for choice in Hostel.PAYMENT_MODE]
    if payment_mode not in valid_modes:
        return JsonResponse({
            'success': False,
            'message': 'Invalid payment mode selected.'
        })
    
    # Validate installments_count
    try:
        installments_count = int(installments_count_str)
        if payment_mode == 'installments':
            if installments_count < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Installments count must be at least 1.'
                })
            if installments_count > 12:
                return JsonResponse({
                    'success': False,
                    'message': 'Installments count cannot exceed 12.'
                })
        else:
            installments_count = 1
    except ValueError:
        installments_count = 1
    
    # Check for duplicate name (excluding current)
    if Hostel.objects.filter(name__iexact=name).exclude(id=hostel.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'A hostel with name "{name}" already exists.'
        })
    
    # Check for duplicate code (excluding current)
    if Hostel.objects.filter(code__iexact=code).exclude(id=hostel.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'A hostel with code "{code}" already exists.'
        })
    
    # Get optional field
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Update the hostel
        hostel.name = name
        hostel.code = code
        hostel.hostel_type = hostel_type
        hostel.max_students = max_students
        hostel.total_fee = total_fee
        hostel.payment_mode = payment_mode
        hostel.installments_count = installments_count
        hostel.is_active = is_active
        hostel.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Hostel "{name}" updated successfully.',
            'hostel': {
                'id': hostel.id,
                'name': hostel.name,
                'code': hostel.code,
                'hostel_type': hostel.hostel_type,
                'hostel_type_display': hostel.get_hostel_type_display(),
                'max_students': hostel.max_students,
                'total_fee': float(hostel.total_fee),
                'payment_mode': hostel.payment_mode,
                'payment_mode_display': hostel.get_payment_mode_display(),
                'installments_count': hostel.installments_count,
                'is_active': hostel.is_active
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A hostel with this name or code already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating hostel: {str(e)}'
        })


def toggle_hostel_status(request):
    """Toggle hostel active/inactive status"""
    hostel_id = request.POST.get('id')
    if not hostel_id:
        return JsonResponse({
            'success': False,
            'message': 'Hostel ID is required.'
        })
    
    try:
        hostel = Hostel.objects.get(id=hostel_id)
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Hostel not found.'
        })
    
    try:
        # Toggle the status
        hostel.is_active = not hostel.is_active
        hostel.save()
        
        status_text = "activated" if hostel.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Hostel "{hostel.name}" {status_text} successfully.',
            'is_active': hostel.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling hostel status: {str(e)}'
        })


def delete_hostel(request):
    """Delete a hostel"""
    hostel_id = request.POST.get('id')
    if not hostel_id:
        return JsonResponse({
            'success': False,
            'message': 'Hostel ID is required.'
        })
    
    try:
        hostel = Hostel.objects.get(id=hostel_id)
        hostel_name = hostel.name
        
        # Check if hostel has any rooms
        if hostel.rooms.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete hostel "{hostel_name}". It has associated rooms.'
            })
        
        # Check if hostel has any allocations
        if hasattr(hostel, 'studenthostelallocation_set') and hostel.studenthostelallocation_set.exists():
            return JsonResponse({
                'success': False,
                'message': f'Cannot delete hostel "{hostel_name}". It has student allocations.'
            })
        
        hostel.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Hostel "{hostel_name}" deleted successfully.',
            'id': hostel_id
        })
        
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Hostel not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting hostel: {str(e)}'
        })


# ============================================================================
# HOSTEL ROOM MANAGEMENT VIEWS
# ============================================================================

@login_required
def hostel_rooms_list(request):
    """
    Display hostel rooms management page
    """
    # Get all active hostels for filter dropdown
    hostels = Hostel.objects.filter(is_active=True).order_by('name')
    
    # Get all rooms with hostel info
    rooms = HostelRoom.objects.select_related('hostel').all().order_by('hostel__name', 'room_number')
    
    # Get statistics
    total_rooms = rooms.count()
    active_rooms = rooms.filter(is_active=True).count()
    total_capacity = rooms.aggregate(total=models.Sum('capacity'))['total'] or 0
    
    # Get occupied rooms count (if you have bed allocations)
    # This will need to be updated based on your bed model
    occupied_rooms = 0  # Placeholder
    
    # Get rooms per hostel for chart/data
    rooms_per_hostel = Hostel.objects.annotate(
        room_count=Count('rooms'),
        total_capacity=models.Sum('rooms__capacity')
    ).filter(room_count__gt=0).order_by('-room_count')
    
    context = {
        'rooms': rooms,
        'hostels': hostels,
        'total_rooms': total_rooms,
        'active_rooms': active_rooms,
        'occupied_rooms': occupied_rooms,
        'total_capacity': total_capacity,
        'rooms_per_hostel': rooms_per_hostel,
        'page_title': 'Hostel Rooms Management',
    }
    
    return render(request, 'admin/hostels/rooms_list.html', context)


@login_required
def hostel_rooms_by_hostel(request, hostel_id):
    """
    Get rooms for a specific hostel (AJAX endpoint for dropdowns)
    """
    try:
        hostel = get_object_or_404(Hostel, id=hostel_id, is_active=True)
        rooms = HostelRoom.objects.filter(
            hostel=hostel,
            is_active=True
        ).order_by('room_number')
        
        room_list = []
        for room in rooms:
            # Get current number of beds in this room
            current_beds = Bed.objects.filter(room=room).count()
            available_beds = room.capacity - current_beds
            
            room_list.append({
                'id': room.id,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'current_beds': current_beds,
                'available_beds': available_beds,
                'display': f"Room {room.room_number} (Capacity: {room.capacity}, Available: {available_beds})"
            })
        
        return JsonResponse({
            'success': True,
            'rooms': room_list,
            'hostel_name': hostel.name
        })
        
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Hostel not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def hostel_rooms_crud(request):
    """
    Handle AJAX CRUD operations for hostel rooms
    """
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_hostel_room(request)
            elif action == 'update':
                return update_hostel_room(request)
            elif action == 'toggle_status':
                return toggle_hostel_room_status(request)
            elif action == 'delete':
                return delete_hostel_room(request)
            elif action == 'bulk_create':
                return bulk_create_rooms(request)
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


def create_hostel_room(request):
    """Create a new hostel room"""
    # Get and validate required fields
    hostel_id = request.POST.get('hostel', '').strip()
    room_number = request.POST.get('room_number', '').strip().upper()
    capacity_str = request.POST.get('capacity', '').strip()
    
    if not hostel_id:
        return JsonResponse({
            'success': False,
            'message': 'Hostel selection is required.'
        })
    
    if not room_number:
        return JsonResponse({
            'success': False,
            'message': 'Room number is required.'
        })
    
    if not capacity_str:
        return JsonResponse({
            'success': False,
            'message': 'Capacity is required.'
        })
    
    # Validate room number
    if len(room_number) < 1:
        return JsonResponse({
            'success': False,
            'message': 'Room number must be at least 1 character long.'
        })
    
    if len(room_number) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Room number cannot exceed 20 characters.'
        })
    
    # Validate capacity
    try:
        capacity = int(capacity_str)
        if capacity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be at least 1.'
            })
        if capacity > 20:  # Assuming max 20 students per room
            return JsonResponse({
                'success': False,
                'message': 'Capacity cannot exceed 20 students per room.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Capacity must be a valid number.'
        })
    
    # Get hostel
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected hostel does not exist or is inactive.'
        })
    
    # Check for duplicate room number in the same hostel
    if HostelRoom.objects.filter(hostel=hostel, room_number__iexact=room_number).exists():
        return JsonResponse({
            'success': False,
            'message': f'Room "{room_number}" already exists in {hostel.name}.'
        })
    
    # Check if adding this room would exceed hostel capacity (optional)
    current_total_capacity = HostelRoom.objects.filter(hostel=hostel).aggregate(
        total=models.Sum('capacity')
    )['total'] or 0
    
    if current_total_capacity + capacity > hostel.max_students:
        return JsonResponse({
            'success': False,
            'message': f'Cannot add room. Total capacity would exceed hostel maximum of {hostel.max_students} students.'
        })
    
    # Get optional field
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Create the room
        room = HostelRoom.objects.create(
            hostel=hostel,
            room_number=room_number,
            capacity=capacity,
            is_active=is_active
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Room "{room_number}" created successfully in {hostel.name}.',
            'room': {
                'id': room.id,
                'hostel_id': room.hostel.id,
                'hostel_name': room.hostel.name,
                'hostel_code': room.hostel.code,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'is_active': room.is_active,
                'display': str(room)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'Room "{room_number}" already exists in this hostel.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating room: {str(e)}'
        })


def update_hostel_room(request):
    """Update an existing hostel room"""
    room_id = request.POST.get('id')
    if not room_id:
        return JsonResponse({
            'success': False,
            'message': 'Room ID is required.'
        })
    
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Room not found.'
        })
    
    # Get and validate required fields
    hostel_id = request.POST.get('hostel', '').strip()
    room_number = request.POST.get('room_number', '').strip().upper()
    capacity_str = request.POST.get('capacity', '').strip()
    
    if not hostel_id or not room_number or not capacity_str:
        return JsonResponse({
            'success': False,
            'message': 'Hostel, room number, and capacity are required.'
        })
    
    # Validate room number
    if len(room_number) < 1:
        return JsonResponse({
            'success': False,
            'message': 'Room number must be at least 1 character long.'
        })
    
    if len(room_number) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Room number cannot exceed 20 characters.'
        })
    
    # Validate capacity
    try:
        capacity = int(capacity_str)
        if capacity < 1:
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be at least 1.'
            })
        if capacity > 20:
            return JsonResponse({
                'success': False,
                'message': 'Capacity cannot exceed 20 students per room.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Capacity must be a valid number.'
        })
    
    # Get hostel
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected hostel does not exist or is inactive.'
        })
    
    # Check for duplicate room number in the same hostel (excluding current)
    if HostelRoom.objects.filter(
        hostel=hostel, 
        room_number__iexact=room_number
    ).exclude(id=room.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Room "{room_number}" already exists in {hostel.name}.'
        })
    
    # Check if capacity reduction would affect existing beds/allocations
    if room.capacity > capacity:
        # Check if there are any beds or allocations that would be affected
        # This depends on your bed model - add appropriate checks
        pass
    
    # Check hostel capacity when changing hostel or capacity
    if room.hostel_id != hostel.id or room.capacity != capacity:
        # Calculate total capacity excluding current room
        other_rooms_capacity = HostelRoom.objects.filter(
            hostel=hostel
        ).exclude(id=room.id).aggregate(
            total=models.Sum('capacity')
        )['total'] or 0
        
        if other_rooms_capacity + capacity > hostel.max_students:
            return JsonResponse({
                'success': False,
                'message': f'Cannot update room. Total capacity would exceed hostel maximum of {hostel.max_students} students.'
            })
    
    # Get optional field
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    try:
        # Update the room
        room.hostel = hostel
        room.room_number = room_number
        room.capacity = capacity
        room.is_active = is_active
        room.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Room "{room_number}" updated successfully.',
            'room': {
                'id': room.id,
                'hostel_id': room.hostel.id,
                'hostel_name': room.hostel.name,
                'hostel_code': room.hostel.code,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'is_active': room.is_active,
                'display': str(room)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'Room "{room_number}" already exists in this hostel.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating room: {str(e)}'
        })


def toggle_hostel_room_status(request):
    """Toggle hostel room active/inactive status"""
    room_id = request.POST.get('id')
    if not room_id:
        return JsonResponse({
            'success': False,
            'message': 'Room ID is required.'
        })
    
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Room not found.'
        })
    
    # Check if room has any beds/allocations before deactivating
    if room.is_active:
        # Check if room has any beds or allocations
        # This depends on your bed model
        has_beds = False  # Placeholder - update based on your Bed model
        if has_beds:
            return JsonResponse({
                'success': False,
                'message': f'Cannot deactivate room "{room.room_number}" because it has assigned beds.'
            })
    
    try:
        # Toggle the status
        room.is_active = not room.is_active
        room.save()
        
        status_text = "activated" if room.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Room "{room.room_number}" in {room.hostel.name} {status_text} successfully.',
            'is_active': room.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling room status: {str(e)}'
        })


def delete_hostel_room(request):
    """Delete a hostel room"""
    room_id = request.POST.get('id')
    if not room_id:
        return JsonResponse({
            'success': False,
            'message': 'Room ID is required.'
        })
    
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Room not found.'
        })
    
    # Check if room has any beds or allocations
    # This depends on your bed model
    has_beds = False  # Placeholder - update based on your Bed model
    
    if has_beds:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete room "{room.room_number}" because it has assigned beds. Remove beds first.'
        })
    
    room_info = f'"{room.room_number}" in {room.hostel.name}'
    
    try:
        room.delete()
        return JsonResponse({
            'success': True,
            'message': f'Room {room_info} deleted successfully.',
            'id': room_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting room: {str(e)}'
        })


def bulk_create_rooms(request):
    """Create multiple rooms at once for a hostel"""
    hostel_id = request.POST.get('hostel', '').strip()
    start_room = request.POST.get('start_room', '').strip().upper()
    end_room = request.POST.get('end_room', '').strip().upper()
    capacity_str = request.POST.get('capacity', '').strip()
    
    if not hostel_id:
        return JsonResponse({
            'success': False,
            'message': 'Hostel selection is required.'
        })
    
    if not start_room or not end_room:
        return JsonResponse({
            'success': False,
            'message': 'Start and end room numbers are required.'
        })
    
    if not capacity_str:
        return JsonResponse({
            'success': False,
            'message': 'Capacity is required.'
        })
    
    # Validate capacity
    try:
        capacity = int(capacity_str)
        if capacity < 1 or capacity > 20:
            return JsonResponse({
                'success': False,
                'message': 'Capacity must be between 1 and 20.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Capacity must be a valid number.'
        })
    
    # Get hostel
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected hostel does not exist or is inactive.'
        })
    
    # Parse room range (assuming alphanumeric room numbers like 101, 102 or A1, A2)
    # This is a simple implementation - you might need more complex logic
    
    # For numeric rooms
    if start_room.isdigit() and end_room.isdigit():
        start_num = int(start_room)
        end_num = int(end_room)
        
        if start_num > end_num:
            return JsonResponse({
                'success': False,
                'message': 'Start room number must be less than or equal to end room number.'
            })
        
        if end_num - start_num > 50:
            return JsonResponse({
                'success': False,
                'message': 'Cannot create more than 50 rooms at once.'
            })
        
        room_numbers = [str(i).zfill(len(start_room)) for i in range(start_num, end_num + 1)]
    else:
        # For alphanumeric, just create the two specified rooms
        room_numbers = [start_room, end_room] if start_room != end_room else [start_room]
    
    created_count = 0
    failed_rooms = []
    
    with transaction.atomic():
        for room_num in room_numbers:
            try:
                # Check if room already exists
                if HostelRoom.objects.filter(hostel=hostel, room_number__iexact=room_num).exists():
                    failed_rooms.append(f"{room_num} (Already exists)")
                    continue
                
                # Check hostel capacity
                current_total = HostelRoom.objects.filter(hostel=hostel).aggregate(
                    total=models.Sum('capacity')
                )['total'] or 0
                
                if current_total + capacity > hostel.max_students:
                    failed_rooms.append(f"{room_num} (Would exceed hostel capacity)")
                    continue
                
                # Create room
                HostelRoom.objects.create(
                    hostel=hostel,
                    room_number=room_num,
                    capacity=capacity,
                    is_active=True
                )
                created_count += 1
                
            except Exception as e:
                failed_rooms.append(f"{room_num} ({str(e)})")
    
    message = f'Successfully created {created_count} room(s) in {hostel.name}.'
    if failed_rooms:
        message += f' Failed: {", ".join(failed_rooms[:5])}'
        if len(failed_rooms) > 5:
            message += f' and {len(failed_rooms) - 5} more.'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'created_count': created_count,
        'failed_count': len(failed_rooms)
    })        


# ============================================================================
# BED MANAGEMENT VIEWS
# ============================================================================

@login_required
def beds_list(request):
    """
    Display beds management page
    """
    # Get all active hostels and rooms for filters
    hostels = Hostel.objects.filter(is_active=True).order_by('name')
    rooms = HostelRoom.objects.select_related('hostel').filter(is_active=True).order_by('hostel__name', 'room_number')
    
    # Get all beds with room and hostel info
    beds = Bed.objects.select_related(
        'room__hostel'
    ).all().order_by('room__hostel__name', 'room__room_number', 'bed_number')
    
    # Get statistics
    total_beds = beds.count()
    occupied_beds = beds.filter(is_occupied=True).count()
    available_beds = total_beds - occupied_beds
    occupancy_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0
    
    # Get bed type distribution
    single_beds = beds.filter(bed_type='single').count()
    bunk_upper = beds.filter(bed_type='bunk_upper').count()
    bunk_lower = beds.filter(bed_type='bunk_lower').count()
    
    # Get beds per hostel
    beds_per_hostel = Hostel.objects.annotate(
        bed_count=Count('rooms__beds'),
        occupied_count=Count('rooms__beds', filter=Q(rooms__beds__is_occupied=True))
    ).filter(bed_count__gt=0).order_by('-bed_count')
    
    context = {
        'beds': beds,
        'hostels': hostels,
        'rooms': rooms,
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'available_beds': available_beds,
        'occupancy_rate': occupancy_rate,
        'single_beds': single_beds,
        'bunk_upper': bunk_upper,
        'bunk_lower': bunk_lower,
        'beds_per_hostel': beds_per_hostel,
        'bed_types': Bed.BED_TYPES,
        'page_title': 'Bed Management',
    }
    
    return render(request, 'admin/hostels/beds_list.html', context)


@login_required
def beds_by_room(request, room_id):
    """
    Get beds for a specific room (AJAX endpoint for dropdowns)
    """
    try:
        room = get_object_or_404(HostelRoom, id=room_id, is_active=True)
        beds = Bed.objects.filter(
            room=room
        ).order_by('bed_number')
        
        bed_list = []
        for bed in beds:
            bed_list.append({
                'id': bed.id,
                'bed_number': bed.bed_number,
                'bed_type': bed.bed_type,
                'bed_type_display': bed.get_bed_type_display(),
                'is_occupied': bed.is_occupied,
                'display': f"Bed {bed.bed_number} ({bed.get_bed_type_display()})" + (" - Occupied" if bed.is_occupied else "")
            })
        
        # Calculate room occupancy
        total_beds = beds.count()
        occupied_beds = beds.filter(is_occupied=True).count()
        available_beds = total_beds - occupied_beds
        
        return JsonResponse({
            'success': True,
            'beds': bed_list,
            'room_number': room.room_number,
            'hostel_name': room.hostel.name,
            'room_capacity': room.capacity,
            'total_beds': total_beds,
            'occupied_beds': occupied_beds,
            'available_beds': available_beds,
            'current_beds': total_beds
        })
        
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Room not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def hostel_rooms_by_hostel(request, hostel_id):
    """
    Get rooms for a specific hostel (AJAX endpoint for dropdowns)
    Used by: const url = '{% url "admin_hostel_rooms_by_hostel" 0 %}'.replace('0', hostelId);
    """
    try:
        # Get the hostel with proper error handling
        if not hostel_id:
            return JsonResponse({
                'success': False,
                'message': 'Hostel ID is required.'
            })
        
        # Get hostel and verify it exists and is active
        try:
            hostel = Hostel.objects.get(id=hostel_id, is_active=True)
        except Hostel.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Hostel not found or is inactive.'
            })
        
        # Get all active rooms for this hostel
        rooms = HostelRoom.objects.filter(
            hostel=hostel,
            is_active=True
        ).order_by('room_number')
        
        room_list = []
        for room in rooms:
            # Get current number of beds in this room
            current_beds = Bed.objects.filter(room=room).count()
            occupied_beds = Bed.objects.filter(room=room, is_occupied=True).count()
            available_beds = room.capacity - current_beds
            vacant_beds = current_beds - occupied_beds
            
            # Create display text with useful information
            display_text = f"Room {room.room_number}"
            display_text += f" (Capacity: {room.capacity}"
            display_text += f", Beds: {current_beds}/{room.capacity}"
            if available_beds > 0:
                display_text += f", {available_beds} slots available"
            display_text += ")"
            
            room_list.append({
                'id': room.id,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'current_beds': current_beds,
                'occupied_beds': occupied_beds,
                'vacant_beds': vacant_beds,
                'available_beds': available_beds,
                'is_full': current_beds >= room.capacity,
                'has_available_slots': available_beds > 0,
                'display': display_text
            })
        
        # Get hostel statistics
        total_rooms = len(room_list)
        total_capacity = sum(room['capacity'] for room in room_list)
        total_beds = sum(room['current_beds'] for room in room_list)
        total_available = sum(room['available_beds'] for room in room_list)
        
        return JsonResponse({
            'success': True,
            'rooms': room_list,
            'hostel': {
                'id': hostel.id,
                'name': hostel.name,
                'code': hostel.code,
                'hostel_type': hostel.hostel_type,
                'hostel_type_display': hostel.get_hostel_type_display(),
                'max_students': hostel.max_students,
                'total_rooms': total_rooms,
                'total_capacity': total_capacity,
                'total_beds': total_beds,
                'total_available': total_available,
                'is_active': hostel.is_active
            },
            'statistics': {
                'total_rooms': total_rooms,
                'total_capacity': total_capacity,
                'total_beds': total_beds,
                'total_available': total_available,
                'occupancy_rate': round((total_beds / total_capacity * 100), 1) if total_capacity > 0 else 0
            }
        })
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in hostel_rooms_by_hostel: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'message': f'An error occurred while loading rooms: {str(e)}'
        })

@login_required
def beds_crud(request):
    """
    Handle AJAX CRUD operations for beds
    """
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_bed(request)
            elif action == 'update':
                return update_bed(request)
            elif action == 'toggle_occupancy':
                return toggle_bed_occupancy(request)
            elif action == 'delete':
                return delete_bed(request)
            elif action == 'bulk_create':
                return bulk_create_beds(request)
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


def create_bed(request):
    """Create a new bed in a room"""
    # Get and validate required fields
    room_id = request.POST.get('room', '').strip()
    bed_number = request.POST.get('bed_number', '').strip().upper()
    bed_type = request.POST.get('bed_type', '').strip()
    
    if not room_id:
        return JsonResponse({
            'success': False,
            'message': 'Room selection is required.'
        })
    
    if not bed_number:
        return JsonResponse({
            'success': False,
            'message': 'Bed number is required.'
        })
    
    if not bed_type:
        return JsonResponse({
            'success': False,
            'message': 'Bed type is required.'
        })
    
    # Validate bed number
    if len(bed_number) < 1:
        return JsonResponse({
            'success': False,
            'message': 'Bed number must be at least 1 character long.'
        })
    
    if len(bed_number) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Bed number cannot exceed 20 characters.'
        })
    
    # Validate bed number format (alphanumeric with optional hyphen)
    if not bed_number.replace('-', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Bed number can only contain letters, numbers, and hyphens.'
        })
    
    # Validate bed type
    valid_types = [choice[0] for choice in Bed.BED_TYPES]
    if bed_type not in valid_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid bed type selected.'
        })
    
    # Get room
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id, is_active=True)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected room does not exist or is inactive.'
        })
    
    # Check for duplicate bed number in the same room
    if Bed.objects.filter(room=room, bed_number__iexact=bed_number).exists():
        return JsonResponse({
            'success': False,
            'message': f'Bed "{bed_number}" already exists in Room {room.room_number}.'
        })
    
    # Check room capacity
    current_beds_count = Bed.objects.filter(room=room).count()
    if current_beds_count >= room.capacity:
        return JsonResponse({
            'success': False,
            'message': f'Cannot add more beds. Room capacity is {room.capacity} beds.'
        })
    
    # Check if adding a bunk bed makes sense (optional validation)
    if bed_type in ['bunk_upper', 'bunk_lower']:
        # Check if the corresponding bunk bed exists or can be added
        other_bunk = 'bunk_lower' if bed_type == 'bunk_upper' else 'bunk_upper'
        # This is just a warning, not an error
        pass
    
    # Get optional field
    is_occupied = request.POST.get('is_occupied') == 'on' or request.POST.get('is_occupied') == 'true'
    
    try:
        # Create the bed
        bed = Bed.objects.create(
            room=room,
            bed_number=bed_number,
            bed_type=bed_type,
            is_occupied=is_occupied
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Bed "{bed_number}" created successfully in Room {room.room_number}.',
            'bed': {
                'id': bed.id,
                'room_id': bed.room.id,
                'room_number': bed.room.room_number,
                'hostel_id': bed.room.hostel.id,
                'hostel_name': bed.room.hostel.name,
                'hostel_code': bed.room.hostel.code,
                'bed_number': bed.bed_number,
                'bed_type': bed.bed_type,
                'bed_type_display': bed.get_bed_type_display(),
                'is_occupied': bed.is_occupied,
                'display': str(bed)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'Bed "{bed_number}" already exists in this room.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating bed: {str(e)}'
        })


def update_bed(request):
    """Update an existing bed"""
    bed_id = request.POST.get('id')
    if not bed_id:
        return JsonResponse({
            'success': False,
            'message': 'Bed ID is required.'
        })
    
    try:
        bed = Bed.objects.select_related('room__hostel').get(id=bed_id)
    except Bed.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Bed not found.'
        })
    
    # Get and validate required fields
    room_id = request.POST.get('room', '').strip()
    bed_number = request.POST.get('bed_number', '').strip().upper()
    bed_type = request.POST.get('bed_type', '').strip()
    
    if not room_id or not bed_number or not bed_type:
        return JsonResponse({
            'success': False,
            'message': 'Room, bed number, and bed type are required.'
        })
    
    # Validate bed number
    if len(bed_number) < 1:
        return JsonResponse({
            'success': False,
            'message': 'Bed number must be at least 1 character long.'
        })
    
    if len(bed_number) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Bed number cannot exceed 20 characters.'
        })
    
    # Validate bed number format
    if not bed_number.replace('-', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Bed number can only contain letters, numbers, and hyphens.'
        })
    
    # Validate bed type
    valid_types = [choice[0] for choice in Bed.BED_TYPES]
    if bed_type not in valid_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid bed type selected.'
        })
    
    # Get room
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id, is_active=True)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected room does not exist or is inactive.'
        })
    
    # Check for duplicate bed number in the same room (excluding current)
    if Bed.objects.filter(
        room=room, 
        bed_number__iexact=bed_number
    ).exclude(id=bed.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Bed "{bed_number}" already exists in Room {room.room_number}.'
        })
    
    # Check room capacity when moving to different room
    if bed.room_id != room.id:
        current_beds_count = Bed.objects.filter(room=room).count()
        if current_beds_count >= room.capacity:
            return JsonResponse({
                'success': False,
                'message': f'Cannot move bed. Target room capacity is {room.capacity} beds.'
            })
    
    # Get optional field
    is_occupied = request.POST.get('is_occupied') == 'on' or request.POST.get('is_occupied') == 'true'
    
    try:
        # Update the bed
        bed.room = room
        bed.bed_number = bed_number
        bed.bed_type = bed_type
        bed.is_occupied = is_occupied
        bed.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Bed "{bed_number}" updated successfully.',
            'bed': {
                'id': bed.id,
                'room_id': bed.room.id,
                'room_number': bed.room.room_number,
                'hostel_id': bed.room.hostel.id,
                'hostel_name': bed.room.hostel.name,
                'hostel_code': bed.room.hostel.code,
                'bed_number': bed.bed_number,
                'bed_type': bed.bed_type,
                'bed_type_display': bed.get_bed_type_display(),
                'is_occupied': bed.is_occupied,
                'display': str(bed)
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'Bed "{bed_number}" already exists in this room.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating bed: {str(e)}'
        })


def toggle_bed_occupancy(request):
    """Toggle bed occupancy status"""
    bed_id = request.POST.get('id')
    if not bed_id:
        return JsonResponse({
            'success': False,
            'message': 'Bed ID is required.'
        })
    
    try:
        bed = Bed.objects.select_related('room__hostel').get(id=bed_id)
    except Bed.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Bed not found.'
        })
    
    try:
        # Toggle the occupancy
        bed.is_occupied = not bed.is_occupied
        bed.save()
        
        status_text = "occupied" if bed.is_occupied else "vacant"
        
        return JsonResponse({
            'success': True,
            'message': f'Bed "{bed.bed_number}" in Room {bed.room.room_number} marked as {status_text}.',
            'is_occupied': bed.is_occupied
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling bed occupancy: {str(e)}'
        })


def delete_bed(request):
    """Delete a bed"""
    bed_id = request.POST.get('id')
    if not bed_id:
        return JsonResponse({
            'success': False,
            'message': 'Bed ID is required.'
        })
    
    try:
        bed = Bed.objects.select_related('room__hostel').get(id=bed_id)
    except Bed.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Bed not found.'
        })
    
    # Check if bed is occupied
    if bed.is_occupied:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete occupied bed "{bed.bed_number}". Please vacate it first.'
        })
    
    # Check if bed has any allocations (if you have allocation model)
    # This depends on your allocation model
    has_allocations = False  # Placeholder
    
    if has_allocations:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete bed "{bed.bed_number}" because it has student allocations.'
        })
    
    bed_info = f'Bed "{bed.bed_number}" in Room {bed.room.room_number} ({bed.room.hostel.name})'
    
    try:
        bed.delete()
        return JsonResponse({
            'success': True,
            'message': f'{bed_info} deleted successfully.',
            'id': bed_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting bed: {str(e)}'
        })


def bulk_create_beds(request):
    """Create multiple beds at once for a room"""
    room_id = request.POST.get('room', '').strip()
    start_bed = request.POST.get('start_bed', '').strip().upper()
    end_bed = request.POST.get('end_bed', '').strip().upper()
    bed_type = request.POST.get('bed_type', '').strip()
    
    if not room_id:
        return JsonResponse({
            'success': False,
            'message': 'Room selection is required.'
        })
    
    if not start_bed or not end_bed:
        return JsonResponse({
            'success': False,
            'message': 'Start and end bed numbers are required.'
        })
    
    if not bed_type:
        return JsonResponse({
            'success': False,
            'message': 'Bed type is required.'
        })
    
    # Validate bed type
    valid_types = [choice[0] for choice in Bed.BED_TYPES]
    if bed_type not in valid_types:
        return JsonResponse({
            'success': False,
            'message': 'Invalid bed type selected.'
        })
    
    # Get room
    try:
        room = HostelRoom.objects.select_related('hostel').get(id=room_id, is_active=True)
    except HostelRoom.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected room does not exist or is inactive.'
        })
    
    # Parse bed range (assuming numeric bed numbers)
    if start_bed.isdigit() and end_bed.isdigit():
        start_num = int(start_bed)
        end_num = int(end_bed)
        
        if start_num > end_num:
            return JsonResponse({
                'success': False,
                'message': 'Start bed number must be less than or equal to end bed number.'
            })
        
        if end_num - start_num > 20:
            return JsonResponse({
                'success': False,
                'message': 'Cannot create more than 20 beds at once.'
            })
        
        bed_numbers = [str(i).zfill(len(start_bed)) for i in range(start_num, end_num + 1)]
    else:
        # For alphanumeric, just create the two specified beds
        bed_numbers = [start_bed, end_bed] if start_bed != end_bed else [start_bed]
    
    # Check room capacity
    current_beds_count = Bed.objects.filter(room=room).count()
    available_slots = room.capacity - current_beds_count
    
    if len(bed_numbers) > available_slots:
        return JsonResponse({
            'success': False,
            'message': f'Cannot create {len(bed_numbers)} beds. Only {available_slots} slots available in this room.'
        })
    
    created_count = 0
    failed_beds = []
    
    with transaction.atomic():
        for bed_num in bed_numbers:
            try:
                # Check if bed already exists
                if Bed.objects.filter(room=room, bed_number__iexact=bed_num).exists():
                    failed_beds.append(f"{bed_num} (Already exists)")
                    continue
                
                # Create bed
                Bed.objects.create(
                    room=room,
                    bed_number=bed_num,
                    bed_type=bed_type,
                    is_occupied=False
                )
                created_count += 1
                
            except Exception as e:
                failed_beds.append(f"{bed_num} ({str(e)})")
    
    message = f'Successfully created {created_count} bed(s) in Room {room.room_number}.'
    if failed_beds:
        message += f' Failed: {", ".join(failed_beds[:5])}'
        if len(failed_beds) > 5:
            message += f' and {len(failed_beds) - 5} more.'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'created_count': created_count,
        'failed_count': len(failed_beds)
    })    

# ============================================================================
# STUDENT HOSTEL ALLOCATION VIEWS
# ============================================================================

from django.utils import timezone
from django.db.models import Q, Sum, Count, F, Value, CharField
from django.db.models.functions import Concat
from datetime import datetime

@login_required
def student_hostel_allocations_list(request):
    """
    Display student hostel allocations management page
    """
    # Get all allocations with related data
    allocations = StudentHostelAllocation.objects.select_related(
        'student', 'hostel', 'room', 'bed', 'academic_year'
    ).all().order_by('-start_date', 'student__first_name')
    
    # Get active academic year
    active_academic_year = AcademicYear.objects.filter(is_active=True).first()
    
    # Get statistics
    total_allocations = allocations.count()
    active_allocations = allocations.filter(is_active=True).count()
    
    # Get students with no active allocation
    students_with_allocation = allocations.filter(is_active=True).values_list('student_id', flat=True)
    available_students = Student.objects.filter(
        is_active=True,
        status='active'
    ).exclude(id__in=students_with_allocation).count()
    
    # Get hostel occupancy
    hostels = Hostel.objects.filter(is_active=True)
    hostel_stats = []
    for hostel in hostels:
        allocated = allocations.filter(hostel=hostel, is_active=True).count()
        capacity = hostel.max_students
        occupancy_rate = round((allocated / capacity * 100), 1) if capacity > 0 else 0
        hostel_stats.append({
            'hostel': hostel,
            'allocated': allocated,
            'capacity': capacity,
            'available': capacity - allocated,
            'occupancy_rate': occupancy_rate
        })
    
    # Get recent allocations
    recent_allocations = allocations[:10]
    
    context = {
        'allocations': allocations,
        'recent_allocations': recent_allocations,
        'total_allocations': total_allocations,
        'active_allocations': active_allocations,
        'available_students': available_students,
        'hostel_stats': hostel_stats,
        'active_academic_year': active_academic_year,
        'hostels': Hostel.objects.filter(is_active=True),
        'academic_years': AcademicYear.objects.all().order_by('-start_date'),
        'page_title': 'Student Hostel Allocations',
    }
    
    return render(request, 'admin/hostels/student_allocations_list.html', context)


@login_required
def get_available_students(request):
    """
    AJAX endpoint to get students available for allocation
    """
    try:
        # Get parameters
        search = request.GET.get('search', '')
        gender = request.GET.get('gender', '')
        class_level_id = request.GET.get('class_level', '')
        
        # Get students with no active allocation
        students_with_allocation = StudentHostelAllocation.objects.filter(
            is_active=True
        ).values_list('student_id', flat=True)
        
        # Base queryset
        students = Student.objects.filter(
            is_active=True,
            status='active'
        ).exclude(id__in=students_with_allocation)
        
        # Apply search filter using individual fields
        if search:
            students = students.filter(
                Q(first_name__icontains=search) |
                Q(middle_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(registration_number__icontains=search) |
                Q(examination_number__icontains=search)
            )
        
        if gender:
            students = students.filter(gender=gender)
        
        if class_level_id:
            students = students.filter(class_level_id=class_level_id)
        
        # Select related to avoid N+1 queries
        students = students.select_related('class_level').only(
            'id', 'first_name', 'middle_name', 'last_name', 
            'registration_number', 'class_level__name'
        )[:50]
        
        student_list = []
        for student in students:
            student_list.append({
                'id': student.id,
                'text': f"{student.full_name} ({student.registration_number}) - {student.class_level.name if student.class_level else 'N/A'}"
            })
        
        return JsonResponse({
            'results': student_list,
            'pagination': {'more': False}
        })
        
    except Exception as e:
        # Log the error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_available_students: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'results': [],
            'error': str(e)
        })


@login_required
def get_available_rooms(request, hostel_id):
    """
    AJAX endpoint to get available rooms in a hostel for allocation
    """
    try:
        hostel = get_object_or_404(Hostel, id=hostel_id, is_active=True)
        
        # Get all active rooms in this hostel
        rooms = HostelRoom.objects.filter(
            hostel=hostel,
            is_active=True
        ).order_by('room_number')
        
        room_list = []
        for room in rooms:
            # Count current beds and allocations
            total_beds = Bed.objects.filter(room=room).count()
            occupied_beds = Bed.objects.filter(room=room, is_occupied=True).count()
            
            # Get active allocations in this room
            active_allocations = StudentHostelAllocation.objects.filter(
                room=room,
                is_active=True
            ).count()
            
            # Calculate available spaces
            available_spaces = room.capacity - active_allocations
            
            room_list.append({
                'id': room.id,
                'room_number': room.room_number,
                'capacity': room.capacity,
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'active_allocations': active_allocations,
                'available_spaces': available_spaces,
                'has_available_spaces': available_spaces > 0,
                'display': f"Room {room.room_number} - {active_allocations}/{room.capacity} students"
            })
        
        return JsonResponse({
            'success': True,
            'rooms': room_list,
            'hostel_name': hostel.name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def get_available_beds(request, room_id):
    """
    AJAX endpoint to get available beds in a room for allocation
    """
    try:
        room = get_object_or_404(HostelRoom, id=room_id, is_active=True)
        
        # Get beds that are not occupied and not allocated
        occupied_bed_ids = StudentHostelAllocation.objects.filter(
            bed__isnull=False,
            is_active=True
        ).values_list('bed_id', flat=True)
        
        available_beds = Bed.objects.filter(
            room=room,
            is_occupied=False
        ).exclude(id__in=occupied_bed_ids).order_by('bed_number')
        
        bed_list = []
        for bed in available_beds:
            bed_list.append({
                'id': bed.id,
                'bed_number': bed.bed_number,
                'bed_type': bed.bed_type,
                'bed_type_display': bed.get_bed_type_display(),
                'display': f"Bed {bed.bed_number} ({bed.get_bed_type_display()})"
            })
        
        # Get current allocations count
        current_allocations = StudentHostelAllocation.objects.filter(
            room=room,
            is_active=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'beds': bed_list,
            'room_number': room.room_number,
            'current_allocations': current_allocations,
            'room_capacity': room.capacity,
            'available_spaces': room.capacity - current_allocations,
            'has_available_beds': len(bed_list) > 0
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def check_availability(request):
    """
    AJAX endpoint to check if a specific combination is available
    """
    try:
        hostel_id = request.GET.get('hostel_id')
        room_id = request.GET.get('room_id')
        bed_id = request.GET.get('bed_id')
        
        response = {'success': True, 'available': True, 'messages': []}
        
        # Check hostel capacity
        if hostel_id:
            hostel = Hostel.objects.get(id=hostel_id)
            current_allocations = StudentHostelAllocation.objects.filter(
                hostel=hostel,
                is_active=True
            ).count()
            
            if current_allocations >= hostel.max_students:
                response['available'] = False
                response['messages'].append(f"Hostel {hostel.name} is full")
        
        # Check room availability
        if room_id and response['available']:
            room = HostelRoom.objects.get(id=room_id)
            current_allocations = StudentHostelAllocation.objects.filter(
                room=room,
                is_active=True
            ).count()
            
            if current_allocations >= room.capacity:
                response['available'] = False
                response['messages'].append(f"Room {room.room_number} is full")
        
        # Check bed availability
        if bed_id and response['available']:
            bed = Bed.objects.get(id=bed_id)
            if bed.is_occupied:
                response['available'] = False
                response['messages'].append(f"Bed {bed.bed_number} is already occupied")
        
        return JsonResponse(response)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


@login_required
def student_hostel_allocations_crud(request):
    """
    Handle AJAX CRUD operations for student hostel allocations
    """
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_allocation(request)
            elif action == 'update':
                return update_allocation(request)
            elif action == 'toggle_status':
                return toggle_allocation_status(request)
            elif action == 'delete':
                return delete_allocation(request)
            elif action == 'bulk_create':
                return bulk_create_allocations(request)
            elif action == 'vacate':
                return vacate_allocation(request)
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


def create_allocation(request):
    """Create a new student hostel allocation"""
    # Get required fields
    student_id = request.POST.get('student', '').strip()
    hostel_id = request.POST.get('hostel', '').strip()
    academic_year_id = request.POST.get('academic_year', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    
    # Optional fields
    room_id = request.POST.get('room', '').strip()
    bed_id = request.POST.get('bed', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    
    # Validate required fields
    if not student_id:
        return JsonResponse({'success': False, 'message': 'Student is required.'})
    if not hostel_id:
        return JsonResponse({'success': False, 'message': 'Hostel is required.'})
    if not academic_year_id:
        return JsonResponse({'success': False, 'message': 'Academic year is required.'})
    if not start_date:
        return JsonResponse({'success': False, 'message': 'Start date is required.'})
    
    # Validate student
    try:
        student = Student.objects.get(id=student_id, is_active=True)
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found or inactive.'})
    
    # Check if student already has active allocation
    if StudentHostelAllocation.objects.filter(student=student, is_active=True).exists():
        return JsonResponse({
            'success': False, 
            'message': f'Student {student.full_name} already has an active allocation.'
        })
    
    # Validate hostel
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
    except Hostel.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Hostel not found or inactive.'})
    
    # Check hostel capacity
    current_allocations = StudentHostelAllocation.objects.filter(
        hostel=hostel, 
        is_active=True
    ).count()
    
    if current_allocations >= hostel.max_students:
        return JsonResponse({
            'success': False,
            'message': f'Hostel {hostel.name} has reached maximum capacity ({hostel.max_students} students).'
        })
    
    # Validate academic year
    try:
        academic_year = AcademicYear.objects.get(id=academic_year_id)
    except AcademicYear.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Academic year not found.'})
    
    # Validate room if provided
    room = None
    if room_id:
        try:
            room = HostelRoom.objects.get(id=room_id, hostel=hostel, is_active=True)
            
            # Check room capacity
            room_allocations = StudentHostelAllocation.objects.filter(
                room=room,
                is_active=True
            ).count()
            
            if room_allocations >= room.capacity:
                return JsonResponse({
                    'success': False,
                    'message': f'Room {room.room_number} has reached maximum capacity.'
                })
                
        except HostelRoom.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Room not found or does not belong to selected hostel.'})
    
    # Validate bed if provided
    bed = None
    if bed_id:
        if not room:
            return JsonResponse({
                'success': False, 
                'message': 'Room must be selected when assigning a specific bed.'
            })
        
        try:
            bed = Bed.objects.get(id=bed_id, room=room, is_occupied=False)
            
            # Check if bed is already allocated
            if StudentHostelAllocation.objects.filter(bed=bed, is_active=True).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Bed {bed.bed_number} is already allocated.'
                })
                
            # Mark bed as occupied
            bed.is_occupied = True
            bed.save()
            
        except Bed.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Bed not found or already occupied.'})
    
    # Validate dates
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid start date format.'})
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            if end_date <= start_date:
                return JsonResponse({
                    'success': False, 
                    'message': 'End date must be after start date.'
                })
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid end date format.'})
    else:
        # Set default end date to end of academic year if not provided
        if academic_year.end_date:
            end_date = academic_year.end_date
        else:
            end_date = None
    
    try:
        # Create allocation
        allocation = StudentHostelAllocation.objects.create(
            student=student,
            hostel=hostel,
            room=room,
            bed=bed,
            academic_year=academic_year,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully allocated {student.full_name} to {hostel.name}.',
            'allocation': {
                'id': allocation.id,
                'student': student.full_name,
                'student_id': student.id,
                'hostel': hostel.name,
                'hostel_id': hostel.id,
                'room': room.room_number if room else None,
                'bed': bed.bed_number if bed else None,
                'academic_year': str(academic_year),
                'start_date': allocation.start_date.strftime('%Y-%m-%d'),
                'end_date': allocation.end_date.strftime('%Y-%m-%d') if allocation.end_date else None,
                'is_active': allocation.is_active
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating allocation: {str(e)}'
        })


def update_allocation(request):
    """Update an existing allocation"""
    allocation_id = request.POST.get('id')
    if not allocation_id:
        return JsonResponse({'success': False, 'message': 'Allocation ID is required.'})
    
    try:
        allocation = StudentHostelAllocation.objects.select_related(
            'student', 'hostel', 'room', 'bed', 'academic_year'
        ).get(id=allocation_id)
    except StudentHostelAllocation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Allocation not found.'})
    
    # Get fields
    room_id = request.POST.get('room', '').strip()
    bed_id = request.POST.get('bed', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    is_active = request.POST.get('is_active') == 'on' or request.POST.get('is_active') == 'true'
    
    # Validate room if changing
    room = allocation.room
    if room_id and str(allocation.room_id) != room_id:
        try:
            room = HostelRoom.objects.get(id=room_id, hostel=allocation.hostel, is_active=True)
            
            # Check room capacity
            room_allocations = StudentHostelAllocation.objects.filter(
                room=room,
                is_active=True
            ).exclude(id=allocation.id).count()
            
            if room_allocations >= room.capacity:
                return JsonResponse({
                    'success': False,
                    'message': f'Room {room.room_number} has reached maximum capacity.'
                })
                
        except HostelRoom.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Room not found.'})
    
    # Validate bed if changing
    bed = allocation.bed
    if bed_id and str(allocation.bed_id) != bed_id:
        if not room:
            return JsonResponse({
                'success': False, 
                'message': 'Room must be selected when assigning a specific bed.'
            })
        
        try:
            bed = Bed.objects.get(id=bed_id, room=room, is_occupied=False)
            
            # Check if bed is already allocated
            if StudentHostelAllocation.objects.filter(bed=bed, is_active=True).exclude(id=allocation.id).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Bed {bed.bed_number} is already allocated.'
                })
                
            # Free old bed if exists
            if allocation.bed:
                allocation.bed.is_occupied = False
                allocation.bed.save()
                
            # Mark new bed as occupied
            bed.is_occupied = True
            bed.save()
            
        except Bed.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Bed not found or already occupied.'})
    
    # Validate end date
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            if end_date <= allocation.start_date:
                return JsonResponse({
                    'success': False, 
                    'message': 'End date must be after start date.'
                })
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid end date format.'})
    else:
        end_date = None
    
    try:
        # Update allocation
        if room:
            allocation.room = room
        if bed:
            allocation.bed = bed
        if end_date:
            allocation.end_date = end_date
        
        # Handle status change
        if allocation.is_active != is_active:
            allocation.is_active = is_active
            if allocation.bed:
                allocation.bed.is_occupied = is_active
                allocation.bed.save()
        
        allocation.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Allocation for {allocation.student.full_name} updated successfully.',
            'allocation': {
                'id': allocation.id,
                'is_active': allocation.is_active
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating allocation: {str(e)}'
        })


def toggle_allocation_status(request):
    """Toggle allocation active/inactive status"""
    allocation_id = request.POST.get('id')
    if not allocation_id:
        return JsonResponse({'success': False, 'message': 'Allocation ID is required.'})
    
    try:
        allocation = StudentHostelAllocation.objects.select_related('bed').get(id=allocation_id)
    except StudentHostelAllocation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Allocation not found.'})
    
    try:
        # Toggle status
        allocation.is_active = not allocation.is_active
        
        # Update bed occupancy
        if allocation.bed:
            allocation.bed.is_occupied = allocation.is_active
            allocation.bed.save()
        
        # If deactivating, set end date to now
        if not allocation.is_active and not allocation.end_date:
            allocation.end_date = timezone.now().date()
        
        allocation.save()
        
        status_text = "activated" if allocation.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Allocation for {allocation.student.full_name} {status_text} successfully.',
            'is_active': allocation.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error toggling allocation status: {str(e)}'
        })


def vacate_allocation(request):
    """Vacate a student allocation (mark as inactive with end date)"""
    allocation_id = request.POST.get('id')
    if not allocation_id:
        return JsonResponse({'success': False, 'message': 'Allocation ID is required.'})
    
    try:
        allocation = StudentHostelAllocation.objects.select_related('bed').get(id=allocation_id)
    except StudentHostelAllocation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Allocation not found.'})
    
    if not allocation.is_active:
        return JsonResponse({'success': False, 'message': 'Allocation is already inactive.'})
    
    try:
        # Deactivate allocation
        allocation.is_active = False
        allocation.end_date = timezone.now().date()
        
        # Free the bed
        if allocation.bed:
            allocation.bed.is_occupied = False
            allocation.bed.save()
        
        allocation.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully vacated {allocation.student.full_name} from {allocation.hostel.name}.',
            'end_date': allocation.end_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error vacating allocation: {str(e)}'
        })


def delete_allocation(request):
    """Delete an allocation (permanent)"""
    allocation_id = request.POST.get('id')
    if not allocation_id:
        return JsonResponse({'success': False, 'message': 'Allocation ID is required.'})
    
    try:
        allocation = StudentHostelAllocation.objects.select_related('bed').get(id=allocation_id)
    except StudentHostelAllocation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Allocation not found.'})
    
    # Free the bed if occupied
    if allocation.bed and allocation.bed.is_occupied:
        allocation.bed.is_occupied = False
        allocation.bed.save()
    
    student_name = allocation.student.full_name
    hostel_name = allocation.hostel.name
    
    try:
        allocation.delete()
        return JsonResponse({
            'success': True,
            'message': f'Allocation for {student_name} to {hostel_name} deleted successfully.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting allocation: {str(e)}'
        })


def bulk_create_allocations(request):
    """Create multiple allocations at once"""
    student_ids = request.POST.getlist('students[]')
    hostel_id = request.POST.get('hostel', '').strip()
    academic_year_id = request.POST.get('academic_year', '').strip()
    start_date = request.POST.get('start_date', '').strip()
    
    if not student_ids:
        return JsonResponse({'success': False, 'message': 'No students selected.'})
    
    if not hostel_id:
        return JsonResponse({'success': False, 'message': 'Hostel is required.'})
    
    if not academic_year_id:
        return JsonResponse({'success': False, 'message': 'Academic year is required.'})
    
    if not start_date:
        return JsonResponse({'success': False, 'message': 'Start date is required.'})
    
    try:
        hostel = Hostel.objects.get(id=hostel_id, is_active=True)
        academic_year = AcademicYear.objects.get(id=academic_year_id)
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    except (Hostel.DoesNotExist, AcademicYear.DoesNotExist, ValueError) as e:
        return JsonResponse({'success': False, 'message': f'Invalid data: {str(e)}'})
    
    # Check hostel capacity
    current_allocations = StudentHostelAllocation.objects.filter(
        hostel=hostel,
        is_active=True
    ).count()
    
    available_slots = hostel.max_students - current_allocations
    
    if len(student_ids) > available_slots:
        return JsonResponse({
            'success': False,
            'message': f'Cannot allocate {len(student_ids)} students. Only {available_slots} slots available in {hostel.name}.'
        })
    
    created_count = 0
    failed_students = []
    
    with transaction.atomic():
        for student_id in student_ids:
            try:
                student = Student.objects.get(id=student_id, is_active=True)
                
                # Check if student already has allocation
                if StudentHostelAllocation.objects.filter(student=student, is_active=True).exists():
                    failed_students.append(f"{student.full_name} (Already allocated)")
                    continue
                
                # Create allocation
                StudentHostelAllocation.objects.create(
                    student=student,
                    hostel=hostel,
                    academic_year=academic_year,
                    start_date=start_date,
                    is_active=True
                )
                created_count += 1
                
            except Exception as e:
                failed_students.append(f"Student ID {student_id} ({str(e)})")
    
    message = f'Successfully allocated {created_count} student(s) to {hostel.name}.'
    if failed_students:
        message += f' Failed: {", ".join(failed_students[:5])}'
        if len(failed_students) > 5:
            message += f' and {len(failed_students) - 5} more.'
    
    return JsonResponse({
        'success': True,
        'message': message,
        'created_count': created_count,
        'failed_count': len(failed_students)
    })


@login_required
def allocation_details(request, allocation_id):
    """
    Get detailed information about a specific allocation (AJAX)
    """
    try:
        allocation = StudentHostelAllocation.objects.select_related(
            'student', 'hostel', 'room', 'bed', 'academic_year'
        ).get(id=allocation_id)
        
        # Get payment information
        payments = allocation.payments.all().order_by('-payment_date')
        
        total_paid = allocation.total_paid
        balance = allocation.balance
        
        data = {
            'id': allocation.id,
            'student': {
                'id': allocation.student.id,
                'full_name': allocation.student.full_name,
                'registration_number': allocation.student.registration_number,
                'gender': allocation.student.gender,
                'class_level': allocation.student.class_level.name if allocation.student.class_level else None,
                'stream': allocation.student.stream_class.stream_letter if allocation.student.stream_class else None,
            },
            'hostel': {
                'id': allocation.hostel.id,
                'name': allocation.hostel.name,
                'code': allocation.hostel.code,
                'total_fee': float(allocation.hostel.total_fee),
            },
            'room': {
                'id': allocation.room.id if allocation.room else None,
                'room_number': allocation.room.room_number if allocation.room else None,
            } if allocation.room else None,
            'bed': {
                'id': allocation.bed.id if allocation.bed else None,
                'bed_number': allocation.bed.bed_number if allocation.bed else None,
                'bed_type': allocation.bed.bed_type if allocation.bed else None,
            } if allocation.bed else None,
            'academic_year': str(allocation.academic_year),
            'start_date': allocation.start_date.strftime('%Y-%m-%d'),
            'end_date': allocation.end_date.strftime('%Y-%m-%d') if allocation.end_date else None,
            'is_active': allocation.is_active,
            'financial': {
                'total_fee': float(allocation.total_fee),
                'total_paid': float(total_paid),
                'balance': float(balance),
                'payment_status': 'Paid' if balance <= 0 else 'Partial' if total_paid > 0 else 'Unpaid',
            },
            'payments': [
                {
                    'id': p.id,
                    'receipt_number': p.receipt_number,
                    'amount_paid': float(p.amount_paid),
                    'payment_date': p.payment_date.strftime('%Y-%m-%d'),
                    'installment': p.installment_plan.installment_number if p.installment_plan else None,
                    'status': p.status,
                }
                for p in payments
            ]
        }
        
        return JsonResponse({
            'success': True,
            'allocation': data
        })
        
    except StudentHostelAllocation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Allocation not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })    