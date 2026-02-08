# results/views/grading_scales.py
import csv
import json
import math
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
import openpyxl
import pandas as pd
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import (require_GET, require_http_methods,
                                          require_POST)

from openpyxl.utils import get_column_letter
from weasyprint import HTML

from core.models import (AcademicYear, ClassLevel, EducationalLevel,
                         StreamClass, Subject, Term)
from results.models import (DivisionScale, ExamSession, ExamType, GradingScale,
                            StudentExamMetrics, StudentExamPosition,
                            StudentResult)
from students.models import Student


@login_required
def grading_scales_list(request):
    """Display grading scales management page"""
    grading_scales = GradingScale.objects.select_related('education_level').all().order_by(
        'education_level__name', '-min_mark'
    )
    
    education_levels = EducationalLevel.objects.filter(is_active=True)
    
    # Get GRADE_CHOICES from model
    grade_choices = GradingScale.GRADE_CHOICES
    
    context = {
        'grading_scales': grading_scales,
        'education_levels': education_levels,
        'grade_choices': grade_choices,
        'page_title': 'Grading Scales Management',
    }
    
    return render(request, 'admin/results/grading_scales_list.html', context)


@login_required
@require_POST
def grading_scales_crud(request):
    """Handle AJAX CRUD operations for grading scales"""
    action = request.POST.get('action', '').lower()
    
    try:
        if action == 'create':
            return create_grading_scale(request)
        elif action == 'update':
            return update_grading_scale(request)
        elif action == 'delete':
            return delete_grading_scale(request)
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


def create_grading_scale(request):
    """Create a new grading scale"""
    education_level_id = request.POST.get('education_level')
    grade = request.POST.get('grade', '').strip()
    min_mark = request.POST.get('min_mark', '').strip()
    max_mark = request.POST.get('max_mark', '').strip()
    points = request.POST.get('points', '0').strip()
    description = request.POST.get('description', '').strip()
    
    # Validate required fields
    if not all([education_level_id, grade, min_mark, max_mark]):
        return JsonResponse({
            'success': False,
            'message': 'Education level, grade, min mark, and max mark are required.'
        })
    
    # Validate grade choice
    valid_grades = [choice[0] for choice in GradingScale.GRADE_CHOICES]
    if grade not in valid_grades:
        return JsonResponse({
            'success': False,
            'message': 'Invalid grade selected.'
        })
    
    # Convert to appropriate types
    try:
        min_mark_val = Decimal(min_mark)
        max_mark_val = Decimal(max_mark)
        points_val = Decimal(points) if points else Decimal('0.0')
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid number format for marks or points.'
        })
    
    # Validate mark ranges
    if min_mark_val < 0 or min_mark_val > 100:
        return JsonResponse({
            'success': False,
            'message': 'Min mark must be between 0 and 100.'
        })
    
    if max_mark_val < 0 or max_mark_val > 100:
        return JsonResponse({
            'success': False,
            'message': 'Max mark must be between 0 and 100.'
        })
    
    if min_mark_val > max_mark_val:
        return JsonResponse({
            'success': False,
            'message': 'Min mark cannot exceed max mark.'
        })
    
    # Get education level
    try:
        education_level = EducationalLevel.objects.get(id=education_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected education level does not exist.'
        })
    
    # Check for duplicate grade in same education level
    if GradingScale.objects.filter(
        education_level=education_level,
        grade=grade
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Grade "{grade}" already exists for {education_level.name}.'
        })
    
    # Check for overlapping mark ranges
    overlapping_scales = GradingScale.objects.filter(
        education_level=education_level,
        min_mark__lt=max_mark_val,
        max_mark__gt=min_mark_val
    )
    
    if overlapping_scales.exists():
        overlapping = overlapping_scales.first()
        return JsonResponse({
            'success': False,
            'message': f'Mark range overlaps with existing grade "{overlapping.grade}" ({overlapping.min_mark}-{overlapping.max_mark}).'
        })
    
    try:
        with transaction.atomic():
            # Create the grading scale
            grading_scale = GradingScale.objects.create(
                education_level=education_level,
                grade=grade,
                min_mark=min_mark_val,
                max_mark=max_mark_val,
                points=points_val,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Grading scale "{grade}" created successfully for {education_level.name}.',
                'grading_scale': {
                    'id': grading_scale.id,
                    'education_level_id': grading_scale.education_level.id,
                    'education_level_name': grading_scale.education_level.name,
                    'grade': grading_scale.grade,
                    'grade_display': grading_scale.get_grade_display(),
                    'min_mark': str(grading_scale.min_mark),
                    'max_mark': str(grading_scale.max_mark),
                    'points': str(grading_scale.points),
                    'description': grading_scale.description
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating grading scale: {str(e)}'
        })


def update_grading_scale(request):
    """Update an existing grading scale"""
    grading_scale_id = request.POST.get('id')
    if not grading_scale_id:
        return JsonResponse({
            'success': False,
            'message': 'Grading scale ID is required.'
        })
    
    try:
        grading_scale = GradingScale.objects.get(id=grading_scale_id)
    except GradingScale.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Grading scale not found.'
        })
    
    education_level_id = request.POST.get('education_level')
    grade = request.POST.get('grade', '').strip()
    min_mark = request.POST.get('min_mark', '').strip()
    max_mark = request.POST.get('max_mark', '').strip()
    points = request.POST.get('points', '').strip()
    description = request.POST.get('description', '').strip()
    
    # Validate required fields
    if not all([education_level_id, grade, min_mark, max_mark]):
        return JsonResponse({
            'success': False,
            'message': 'Education level, grade, min mark, and max mark are required.'
        })
    
    # Validate grade choice
    valid_grades = [choice[0] for choice in GradingScale.GRADE_CHOICES]
    if grade not in valid_grades:
        return JsonResponse({
            'success': False,
            'message': 'Invalid grade selected.'
        })
    
    # Convert to appropriate types
    try:
        min_mark_val = Decimal(min_mark)
        max_mark_val = Decimal(max_mark)
        points_val = Decimal(points) if points else grading_scale.points
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'message': 'Invalid number format for marks or points.'
        })
    
    # Validate mark ranges
    if min_mark_val < 0 or min_mark_val > 100:
        return JsonResponse({
            'success': False,
            'message': 'Min mark must be between 0 and 100.'
        })
    
    if max_mark_val < 0 or max_mark_val > 100:
        return JsonResponse({
            'success': False,
            'message': 'Max mark must be between 0 and 100.'
        })
    
    if min_mark_val > max_mark_val:
        return JsonResponse({
            'success': False,
            'message': 'Min mark cannot exceed max mark.'
        })
    
    # Get education level
    try:
        education_level = EducationalLevel.objects.get(id=education_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected education level does not exist.'
        })
    
    # Check for duplicate grade in same education level (excluding current)
    if GradingScale.objects.filter(
        education_level=education_level,
        grade=grade
    ).exclude(id=grading_scale.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Grade "{grade}" already exists for {education_level.name}.'
        })
    
    # Check for overlapping mark ranges (excluding current)
    overlapping_scales = GradingScale.objects.filter(
        education_level=education_level,
        min_mark__lt=max_mark_val,
        max_mark__gt=min_mark_val
    ).exclude(id=grading_scale.id)
    
    if overlapping_scales.exists():
        overlapping = overlapping_scales.first()
        if overlapping:
            return JsonResponse({
                'success': False,
                'message': f'Mark range overlaps with existing grade "{overlapping.grade}" ({overlapping.min_mark}-{overlapping.max_mark}).'
            })
    
    try:
        with transaction.atomic():
            # Update the grading scale
            grading_scale.education_level = education_level
            grading_scale.grade = grade
            grading_scale.min_mark = min_mark_val
            grading_scale.max_mark = max_mark_val
            grading_scale.points = points_val
            grading_scale.description = description
            grading_scale.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Grading scale "{grade}" updated successfully.',
                'grading_scale': {
                    'id': grading_scale.id,
                    'education_level_id': grading_scale.education_level.id,
                    'education_level_name': grading_scale.education_level.name,
                    'grade': grading_scale.grade,
                    'grade_display': grading_scale.get_grade_display(),
                    'min_mark': str(grading_scale.min_mark),
                    'max_mark': str(grading_scale.max_mark),
                    'points': str(grading_scale.points),
                    'description': grading_scale.description
                }
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating grading scale: {str(e)}'
        })


def delete_grading_scale(request):
    """Delete a grading scale"""
    grading_scale_id = request.POST.get('id')
    if not grading_scale_id:
        return JsonResponse({
            'success': False,
            'message': 'Grading scale ID is required.'
        })
    
    try:
        grading_scale = GradingScale.objects.get(id=grading_scale_id)
        grade_info = f'{grading_scale.grade} ({grading_scale.education_level.name})'
        grading_scale.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Grading scale "{grade_info}" deleted successfully.',
            'id': grading_scale_id
        })
        
    except GradingScale.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Grading scale not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting grading scale: {str(e)}'
        })




@login_required
def division_scales_list(request):
    """Display division scales management page"""
    division_scales = DivisionScale.objects.select_related('education_level').all().order_by('education_level', 'min_points')
    education_levels = EducationalLevel.objects.filter(is_active=True)
    
    context = {
        'division_scales': division_scales,
        'education_levels': education_levels,
        'DIVISION_CHOICES': DivisionScale.DIVISION_CHOICES,
        'page_title': 'Division Scales Management',
    }
    
    return render(request, 'admin/results/division_scales_list.html', context)

@login_required
def division_scales_crud(request):
    """Handle AJAX CRUD operations for division scales"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_division_scale(request)
            elif action == 'update':
                return update_division_scale(request)
            elif action == 'delete':
                return delete_division_scale(request)
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

def create_division_scale(request):
    """Create a new division scale"""
    # Get and validate required fields
    education_level_id = request.POST.get('education_level')
    if not education_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Education level is required.'
        })
    
    division = request.POST.get('division', '').strip()
    if not division:
        return JsonResponse({
            'success': False,
            'message': 'Division is required.'
        })
    
    min_points_str = request.POST.get('min_points', '').strip()
    max_points_str = request.POST.get('max_points', '').strip()
    
    if not min_points_str or not max_points_str:
        return JsonResponse({
            'success': False,
            'message': 'Both minimum and maximum points are required.'
        })
    
    try:
        min_points = int(min_points_str)
        max_points = int(max_points_str)
        
        if min_points < 0 or max_points < 0:
            return JsonResponse({
                'success': False,
                'message': 'Points cannot be negative.'
            })
        
        if min_points > max_points:
            return JsonResponse({
                'success': False,
                'message': 'Minimum points cannot exceed maximum points.'
            })
        
        # Validate points range
        if max_points > 999:
            return JsonResponse({
                'success': False,
                'message': 'Points cannot exceed 999.'
            })
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Points must be valid numbers.'
        })
    
    # Get education level
    try:
        education_level = EducationalLevel.objects.get(id=education_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected education level does not exist.'
        })
    
    # Validate division choice
    valid_divisions = [choice[0] for choice in DivisionScale.DIVISION_CHOICES]
    if division not in valid_divisions:
        return JsonResponse({
            'success': False,
            'message': 'Invalid division selected.'
        })
    
    # Check for duplicate division within the same education level
    if DivisionScale.objects.filter(
        education_level=education_level,
        division=division
    ).exists():
        return JsonResponse({
            'success': False,
            'message': f'Division "{division}" already exists for {education_level.name}.'
        })
    
    # Check for overlapping point ranges
    overlapping_scales = DivisionScale.objects.filter(
        education_level=education_level
    ).filter(
        min_points__lte=max_points,
        max_points__gte=min_points
    )
    
    if overlapping_scales.exists():
        return JsonResponse({
            'success': False,
            'message': f'Point range overlaps with existing division scale(s).'
        })
    
    try:
        # Create the division scale
        division_scale = DivisionScale.objects.create(
            education_level=education_level,
            division=division,
            min_points=min_points,
            max_points=max_points
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Division scale "{division}" created successfully for {education_level.name}.',
            'division_scale': {
                'id': division_scale.id,
                'education_level_id': division_scale.education_level.id,
                'education_level_name': division_scale.education_level.name,
                'division': division_scale.division,
                'division_display': division_scale.get_division_display(),
                'min_points': division_scale.min_points,
                'max_points': division_scale.max_points,
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A division scale with these details already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating division scale: {str(e)}'
        })

def update_division_scale(request):
    """Update an existing division scale"""
    scale_id = request.POST.get('id')
    if not scale_id:
        return JsonResponse({
            'success': False,
            'message': 'Division scale ID is required.'
        })
    
    try:
        division_scale = DivisionScale.objects.get(id=scale_id)
    except DivisionScale.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Division scale not found.'
        })
    
    # Get and validate required fields
    education_level_id = request.POST.get('education_level')
    division = request.POST.get('division', '').strip()
    min_points_str = request.POST.get('min_points', '').strip()
    max_points_str = request.POST.get('max_points', '').strip()
    
    if not all([education_level_id, division, min_points_str, max_points_str]):
        return JsonResponse({
            'success': False,
            'message': 'All fields are required.'
        })
    
    try:
        min_points = int(min_points_str)
        max_points = int(max_points_str)
        
        if min_points < 0 or max_points < 0:
            return JsonResponse({
                'success': False,
                'message': 'Points cannot be negative.'
            })
        
        if min_points > max_points:
            return JsonResponse({
                'success': False,
                'message': 'Minimum points cannot exceed maximum points.'
            })
        
        # Validate points range
        if max_points > 999:
            return JsonResponse({
                'success': False,
                'message': 'Points cannot exceed 999.'
            })
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Points must be valid numbers.'
        })
    
    # Get education level
    try:
        education_level = EducationalLevel.objects.get(id=education_level_id)
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Selected education level does not exist.'
        })
    
    # Validate division choice
    valid_divisions = [choice[0] for choice in DivisionScale.DIVISION_CHOICES]
    if division not in valid_divisions:
        return JsonResponse({
            'success': False,
            'message': 'Invalid division selected.'
        })
    
    # Check for duplicate division within the same education level (excluding current)
    if DivisionScale.objects.filter(
        education_level=education_level,
        division=division
    ).exclude(id=division_scale.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Division "{division}" already exists for {education_level.name}.'
        })
    
    # Check for overlapping point ranges (excluding current)
    overlapping_scales = DivisionScale.objects.filter(
        education_level=education_level
    ).filter(
        min_points__lte=max_points,
        max_points__gte=min_points
    ).exclude(id=division_scale.id)
    
    if overlapping_scales.exists():
        return JsonResponse({
            'success': False,
            'message': f'Point range overlaps with existing division scale(s).'
        })
    
    try:
        # Update the division scale
        division_scale.education_level = education_level
        division_scale.division = division
        division_scale.min_points = min_points
        division_scale.max_points = max_points
        division_scale.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Division scale "{division}" updated successfully.',
            'division_scale': {
                'id': division_scale.id,
                'education_level_id': division_scale.education_level.id,
                'education_level_name': division_scale.education_level.name,
                'division': division_scale.division,
                'division_display': division_scale.get_division_display(),
                'min_points': division_scale.min_points,
                'max_points': division_scale.max_points,
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'A division scale with these details already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating division scale: {str(e)}'
        })

def delete_division_scale(request):
    """Delete a division scale"""
    scale_id = request.POST.get('id')
    if not scale_id:
        return JsonResponse({
            'success': False,
            'message': 'Division scale ID is required.'
        })
    
    try:
        division_scale = DivisionScale.objects.get(id=scale_id)
    except DivisionScale.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Division scale not found.'
        })
    
    # Check if division scale is referenced by any student exam metrics
    if division_scale.studentexammetrics_set.exists():
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete division scale that is referenced by student exam metrics.'
        })
    
    scale_info = f'{division_scale.get_division_display()} ({division_scale.education_level.name})'
    
    try:
        division_scale.delete()
        return JsonResponse({
            'success': True,
            'message': f'Division scale "{scale_info}" deleted successfully.',
            'id': scale_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting division scale: {str(e)}'
        })

@login_required
def get_division_scales_by_level(request):
    """AJAX endpoint to get division scales by education level"""
    education_level_id = request.GET.get('education_level_id')
    
    if not education_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Education level ID is required.'
        })
    
    try:
        division_scales = DivisionScale.objects.filter(
            education_level_id=education_level_id
        ).order_by('min_points')
        
        scales_list = []
        for scale in division_scales:
            scales_list.append({
                'id': scale.id,
                'division': scale.division,
                'division_display': scale.get_division_display(),
                'min_points': scale.min_points,
                'max_points': scale.max_points,
                'range': f"{scale.min_points} - {scale.max_points}"
            })
        
        return JsonResponse({
            'success': True,
            'division_scales': scales_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def calculate_division(request):
    """Calculate division for given points and education level"""
    if request.method == 'POST':
        education_level_id = request.POST.get('education_level_id')
        total_points = request.POST.get('total_points')
        
        if not education_level_id or not total_points:
            return JsonResponse({
                'success': False,
                'message': 'Education level and total points are required.'
            })
        
        try:
            total_points = float(total_points)
            education_level = EducationalLevel.objects.get(id=education_level_id)
            
            # Get division scales for this education level
            division_scale = DivisionScale.objects.filter(
                education_level=education_level,
                min_points__lte=total_points,
                max_points__gte=total_points
            ).first()
            
            if division_scale:
                return JsonResponse({
                    'success': True,
                    'division': division_scale.division,
                    'division_display': division_scale.get_division_display(),
                    'points': total_points,
                    'education_level': education_level.name
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'No division scale found for {total_points} points in {education_level.name}.'
                })
                
        except EducationalLevel.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Education level not found.'
            })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid points value.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error calculating division: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@login_required
def validate_division_scales(request):
    """Validate division scales for an education level"""
    education_level_id = request.GET.get('education_level_id')
    
    if not education_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Education level ID is required.'
        })
    
    try:
        education_level = EducationalLevel.objects.get(id=education_level_id)
        division_scales = DivisionScale.objects.filter(
            education_level=education_level
        ).order_by('min_points')
        
        # Check for gaps in point ranges
        validation_results = []
        has_gaps = False
        previous_max = -1
        
        for i, scale in enumerate(division_scales):
            # Check if there's a gap
            if scale.min_points > previous_max + 1:
                has_gaps = True
                validation_results.append({
                    'type': 'gap',
                    'message': f'Gap between {previous_max} and {scale.min_points} points',
                    'severity': 'warning'
                })
            
            # Check for overlapping ranges
            for j, other_scale in enumerate(division_scales):
                if i != j and scale.min_points <= other_scale.max_points and scale.max_points >= other_scale.min_points:
                    validation_results.append({
                        'type': 'overlap',
                        'message': f'Overlap with {other_scale.get_division_display()}',
                        'severity': 'error'
                    })
            
            previous_max = scale.max_points
        
        # Check if covers all possible points (0-999)
        if division_scales:
            first_scale = division_scales.first()
            last_scale = division_scales.last()
            
            if first_scale.min_points > 0:
                validation_results.append({
                    'type': 'coverage',
                    'message': f'No division for points 0-{first_scale.min_points - 1}',
                    'severity': 'warning'
                })
            
            if last_scale.max_points < 999:
                validation_results.append({
                    'type': 'coverage',
                    'message': f'No division for points {last_scale.max_points + 1}-999',
                    'severity': 'warning'
                })
        
        return JsonResponse({
            'success': True,
            'validation_results': validation_results,
            'has_errors': any(result['severity'] == 'error' for result in validation_results),
            'has_warnings': any(result['severity'] == 'warning' for result in validation_results),
            'total_scales': division_scales.count()
        })
        
    except EducationalLevel.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Education level not found.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error validating division scales: {str(e)}'
        })        


# ============================================================================
# EXAM TYPE MANAGEMENT VIEWS
# ============================================================================

@login_required
def exam_types_list(request):
    """Display exam types management page"""
    exam_types = ExamType.objects.all().order_by('name')
    
    # Statistics
    total_exam_types = exam_types.count()
    
    context = {
        'exam_types': exam_types,
        'total_exam_types': total_exam_types,
        'page_title': 'Exam Types Management',
    }
    
    return render(request, 'admin/results/exam_types_list.html', context)


@login_required
def exam_types_crud(request):
    """Handle AJAX CRUD operations for exam types"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_exam_type(request)
            elif action == 'update':
                return update_exam_type(request)
            elif action == 'delete':
                return delete_exam_type(request)
            elif action == 'bulk_delete':
                return bulk_delete_exam_types(request)
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


def create_exam_type(request):
    """Create a new exam type"""
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Exam type name is required.'
        })
    
    code = request.POST.get('code', '').strip()
    if not code:
        return JsonResponse({
            'success': False,
            'message': 'Exam type code is required.'
        })
    
    weight_str = request.POST.get('weight', '').strip()
    max_score_str = request.POST.get('max_score', '100').strip()
    
    # Validate name and code length
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Exam type name cannot exceed 100 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Exam type code cannot exceed 20 characters.'
        })
    
    # Validate code format (alphanumeric with hyphens/underscores)
    if not code.replace('-', '').replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Exam type code can only contain letters, numbers, hyphens, and underscores.'
        })
    
    # Validate weight
    try:
        weight = float(weight_str)
        if weight < 0 or weight > 100:
            return JsonResponse({
                'success': False,
                'message': 'Weight must be between 0 and 100.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Weight must be a valid number.'
        })
    
    # Validate max score
    try:
        max_score = float(max_score_str)
        if max_score <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Maximum score must be greater than 0.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Maximum score must be a valid number.'
        })
    
    # Get optional field
    description = request.POST.get('description', '').strip()
    
    # Validate description length if provided
    if description and len(description) > 500:
        return JsonResponse({
            'success': False,
            'message': 'Description cannot exceed 500 characters.'
        })
    
    # Check for duplicate code
    if ExamType.objects.filter(code__iexact=code).exists():
        return JsonResponse({
            'success': False,
            'message': f'Exam type with code "{code}" already exists.'
        })
    
    try:
        # Create the exam type
        exam_type = ExamType.objects.create(
            name=name,
            code=code.upper(),  # Store code in uppercase for consistency
            weight=weight,
            max_score=max_score,
            description=description
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Exam type "{name}" created successfully.',
            'exam_type': {
                'id': exam_type.id,
                'name': exam_type.name,
                'code': exam_type.code,
                'weight': float(exam_type.weight),
                'max_score': float(exam_type.max_score),
                'description': exam_type.description
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'An exam type with code "{code}" already exists.'
            })
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating exam type: {str(e)}'
        })


def update_exam_type(request):
    """Update an existing exam type"""
    exam_type_id = request.POST.get('id')
    if not exam_type_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam type ID is required.'
        })
    
    try:
        exam_type = ExamType.objects.get(id=exam_type_id)
    except ExamType.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam type not found.'
        })
    
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip()
    weight_str = request.POST.get('weight', '').strip()
    max_score_str = request.POST.get('max_score', '').strip()
    
    if not all([name, code, weight_str, max_score_str]):
        return JsonResponse({
            'success': False,
            'message': 'All fields are required.'
        })
    
    # Validate name and code length
    if len(name) > 100:
        return JsonResponse({
            'success': False,
            'message': 'Exam type name cannot exceed 100 characters.'
        })
    
    if len(code) > 20:
        return JsonResponse({
            'success': False,
            'message': 'Exam type code cannot exceed 20 characters.'
        })
    
    # Validate code format
    if not code.replace('-', '').replace('_', '').isalnum():
        return JsonResponse({
            'success': False,
            'message': 'Exam type code can only contain letters, numbers, hyphens, and underscores.'
        })
    
    # Validate weight
    try:
        weight = float(weight_str)
        if weight < 0 or weight > 100:
            return JsonResponse({
                'success': False,
                'message': 'Weight must be between 0 and 100.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Weight must be a valid number.'
        })
    
    # Validate max score
    try:
        max_score = float(max_score_str)
        if max_score <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Maximum score must be greater than 0.'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Maximum score must be a valid number.'
        })
    
    # Get optional field
    description = request.POST.get('description', '').strip()
    
    # Validate description length
    if description and len(description) > 500:
        return JsonResponse({
            'success': False,
            'message': 'Description cannot exceed 500 characters.'
        })
    
    # Check for duplicate code (excluding current)
    if ExamType.objects.filter(code__iexact=code).exclude(id=exam_type.id).exists():
        return JsonResponse({
            'success': False,
            'message': f'Exam type with code "{code}" already exists.'
        })
    
    try:
        # Update the exam type
        exam_type.name = name
        exam_type.code = code.upper()
        exam_type.weight = weight
        exam_type.max_score = max_score
        exam_type.description = description
        exam_type.full_clean()  # Run model validation
        exam_type.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Exam type "{name}" updated successfully.',
            'exam_type': {
                'id': exam_type.id,
                'name': exam_type.name,
                'code': exam_type.code,
                'weight': float(exam_type.weight),
                'max_score': float(exam_type.max_score),
                'description': exam_type.description
            }
        })
        
    except IntegrityError as e:
        if 'unique' in str(e).lower():
            return JsonResponse({
                'success': False,
                'message': f'An exam type with code "{code}" already exists.'
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
            'message': f'Error updating exam type: {str(e)}'
        })


def delete_exam_type(request):
    """Delete an exam type"""
    exam_type_id = request.POST.get('id')
    if not exam_type_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam type ID is required.'
        })
    
    try:
        exam_type = ExamType.objects.get(id=exam_type_id)
    except ExamType.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam type not found.'
        })
    
    # Check if exam type is used in any exam sessions
    if exam_type.examsession_set.exists():
        session_count = exam_type.examsession_set.count()
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete exam type "{exam_type.name}". It is used in {session_count} exam session(s).'
        })
    
    exam_type_name = exam_type.name
    
    try:
        exam_type.delete()
        return JsonResponse({
            'success': True,
            'message': f'Exam type "{exam_type_name}" deleted successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting exam type: {str(e)}'
        })


def bulk_delete_exam_types(request):
    """Bulk delete multiple exam types"""
    try:
        exam_type_ids = request.POST.getlist('exam_type_ids[]')
        
        if not exam_type_ids:
            return JsonResponse({
                'success': False,
                'message': 'No exam types selected.'
            })
        
        exam_types = ExamType.objects.filter(id__in=exam_type_ids)
        deletable_types = []
        non_deletable_types = []
        
        for exam_type in exam_types:
            # Check if exam type is used in any exam sessions
            if exam_type.examsession_set.exists():
                non_deletable_types.append(exam_type.name)
            else:
                deletable_types.append(exam_type)
        
        # Delete deletable exam types
        if deletable_types:
            deleted_count = len(deletable_types)
            ExamType.objects.filter(id__in=[et.id for et in deletable_types]).delete()
            
            message = f'Successfully deleted {deleted_count} exam type(s).'
            if non_deletable_types:
                message += f' Could not delete: {", ".join(non_deletable_types[:3])}'
                if len(non_deletable_types) > 3:
                    message += f' and {len(non_deletable_types) - 3} more (used in exam sessions).'
                else:
                    message += ' (used in exam sessions).'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'deleted_count': deleted_count,
                'failed_count': len(non_deletable_types)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'None of the selected exam types can be deleted (all are used in exam sessions).'
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error bulk deleting exam types: {str(e)}'
        })        




@login_required
def exam_sessions_list(request):
    """Display exam sessions management page"""
    # Get all exam sessions with related data
    exam_sessions = ExamSession.objects.select_related(
        'exam_type',
        'academic_year',
        'term',
        'class_level',
        'class_level__educational_level',
        'stream_class'
    ).prefetch_related(
        'papers__subject'
    ).all()
    
    # Get filter parameters
    academic_year_filter = request.GET.get('academic_year', '')
    term_filter = request.GET.get('term', '')
    class_level_filter = request.GET.get('class_level', '')
    stream_filter = request.GET.get('stream', '')
    status_filter = request.GET.get('status', '')
    
    # Apply filters
    if academic_year_filter:
        exam_sessions = exam_sessions.filter(academic_year_id=academic_year_filter)
    
    if term_filter:
        exam_sessions = exam_sessions.filter(term_id=term_filter)
    
    if class_level_filter:
        exam_sessions = exam_sessions.filter(class_level_id=class_level_filter)
    
    if stream_filter:
        exam_sessions = exam_sessions.filter(stream_class_id=stream_filter)
    
    if status_filter:
        exam_sessions = exam_sessions.filter(status=status_filter)
    
    # Count statistics
    total_sessions = exam_sessions.count()
    draft_sessions = exam_sessions.filter(status='draft').count()
    submitted_sessions = exam_sessions.filter(status='submitted').count()
    verified_sessions = exam_sessions.filter(status='verified').count()
    published_sessions = exam_sessions.filter(status='published').count()
    
    # Get data for filters
    academic_years = AcademicYear.objects.all().order_by('-start_date')
    # Only show terms for the selected academic year if filter is applied
    if academic_year_filter:
        terms = Term.objects.filter(academic_year_id=academic_year_filter).order_by('term_number')
    else:
        terms = Term.objects.none()
    
    class_levels = ClassLevel.objects.filter(is_active=True).select_related('educational_level').order_by('order')
    # Only show streams for the selected class if filter is applied
    if class_level_filter:
        streams = StreamClass.objects.filter(class_level_id=class_level_filter, is_active=True)
    else:
        streams = StreamClass.objects.none()
    
    status_choices = ExamSession.STATUS_CHOICES
    
    # Get exam types for form
    exam_types = ExamType.objects.all().order_by('name')
    
    context = {
        'exam_sessions': exam_sessions,
        'academic_years': academic_years,
        'terms': terms,
        'class_levels': class_levels,
        'streams': streams,
        'status_choices': status_choices,
        'exam_types': exam_types,
        'total_sessions': total_sessions,
        'draft_sessions': draft_sessions,
        'submitted_sessions': submitted_sessions,
        'verified_sessions': verified_sessions,
        'published_sessions': published_sessions,
        'page_title': 'Exam Sessions Management',
        'today': timezone.now().date(),
    }
    
    return render(request, 'admin/results/exam_sessions_list.html', context)


@login_required
def get_terms_for_academic_year(request):
    """API endpoint to get terms for a specific academic year"""
    if request.method == 'GET':
        academic_year_id = request.GET.get('academic_year_id')
        
        if academic_year_id:
            try:
                terms = Term.objects.filter(
                    academic_year_id=academic_year_id
                ).order_by('term_number')
                
                terms_data = [{
                    'id': term.id,
                    'text': term.get_term_number_display()
                } for term in terms]
                
                return JsonResponse({
                    'success': True,
                    'terms': terms_data
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Academic year ID is required'
            }, status=400)


@login_required
def get_streams_for_exam_session(request):
    """API endpoint to get streams for a specific class level"""
    if request.method == 'GET':
        class_level_id = request.GET.get('class_level_id')
        
        if class_level_id:
            try:
                streams = StreamClass.objects.filter(
                    class_level_id=class_level_id,
                    is_active=True
                ).order_by('stream_letter')
                
                streams_data = [{
                    'id': stream.id,
                    'text': stream.stream_letter
                } for stream in streams]
                
                return JsonResponse({
                    'success': True,
                    'streams': streams_data
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Class level ID is required'
            }, status=400)


@login_required
def exam_sessions_crud(request):
    """Handle AJAX CRUD operations for exam sessions"""
    if request.method == 'POST':
        action = request.POST.get('action', '').lower()
        
        try:
            if action == 'create':
                return create_exam_session(request)
            elif action == 'update':
                return update_exam_session(request)
            elif action == 'toggle_status':
                return toggle_exam_session_status(request)
            elif action == 'delete':
                return delete_exam_session(request)
            elif action == 'update_status':
                return update_exam_session_status(request)
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

def create_exam_session(request):
    """Create a new exam session"""
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Exam session name is required.'
        })
    
    exam_type_id = request.POST.get('exam_type')
    if not exam_type_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam type is required.'
        })
    
    academic_year_id = request.POST.get('academic_year')
    if not academic_year_id:
        return JsonResponse({
            'success': False,
            'message': 'Academic year is required.'
        })
    
    term_id = request.POST.get('term')
    if not term_id:
        return JsonResponse({
            'success': False,
            'message': 'Term is required.'
        })
    
    class_level_id = request.POST.get('class_level')
    if not class_level_id:
        return JsonResponse({
            'success': False,
            'message': 'Class level is required.'
        })
    
    exam_date_str = request.POST.get('exam_date')
    if not exam_date_str:
        return JsonResponse({
            'success': False,
            'message': 'Exam date is required.'
        })
    
    # Parse exam date
    try:
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid exam date format. Please use YYYY-MM-DD.'
        })
    
    # Get optional fields
    stream_class_id = request.POST.get('stream_class', '').strip()
    stream_class = None
    if stream_class_id:
        try:
            stream_class = StreamClass.objects.get(id=stream_class_id)
        except StreamClass.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected stream class does not exist.'
            })
    
    status = request.POST.get('status', 'draft')
    
    # Validate name length
    if len(name) < 5 or len(name) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Exam session name must be between 5 and 200 characters.'
        })
    
    # Validate date is not in the future for non-draft statuses
    if status != 'draft' and exam_date > date.today():
        return JsonResponse({
            'success': False,
            'message': 'Exam date cannot be in the future for non-draft sessions.'
        })
    
    # Get related objects
    try:
        exam_type = ExamType.objects.get(id=exam_type_id)
        academic_year = AcademicYear.objects.get(id=academic_year_id)
        term = Term.objects.get(id=term_id)
        class_level = ClassLevel.objects.get(id=class_level_id)
    except (ExamType.DoesNotExist, AcademicYear.DoesNotExist, 
            Term.DoesNotExist, ClassLevel.DoesNotExist) as e:
        return JsonResponse({
            'success': False,
            'message': f'Selected item does not exist: {str(e)}'
        })
    
    # Check for duplicate exam session name in same academic year and term
    duplicate_check = ExamSession.objects.filter(
        name__iexact=name,
        academic_year=academic_year,
        term=term,
        class_level=class_level
    )
    
    if stream_class:
        duplicate_check = duplicate_check.filter(stream_class=stream_class)
    else:
        duplicate_check = duplicate_check.filter(stream_class__isnull=True)
    
    if duplicate_check.exists():
        return JsonResponse({
            'success': False,
            'message': f'An exam session with name "{name}" already exists for the selected parameters.'
        })
    
    try:
        # Create the exam session
        exam_session = ExamSession.objects.create(
            name=name,
            exam_type=exam_type,
            academic_year=academic_year,
            term=term,
            class_level=class_level,
            stream_class=stream_class,
            exam_date=exam_date,
            status=status
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Exam session "{name}" created successfully.',
            'exam_session': {
                'id': exam_session.id,
                'name': exam_session.name,
                'exam_type_name': exam_session.exam_type.name,
                'academic_year_name': exam_session.academic_year.name,
                'term_name': f'{exam_session.term.get_term_number_display()}',
                'class_level_name': exam_session.class_level.name,
                'stream_class_name': str(exam_session.stream_class) if exam_session.stream_class else 'All Streams',
                'exam_date': exam_session.exam_date.strftime('%Y-%m-%d'),
                'status': exam_session.status,
                'status_display': exam_session.get_status_display()
            }
        })
        
    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error creating exam session: {str(e)}'
        })

def update_exam_session(request):
    """Update an existing exam session"""
    exam_session_id = request.POST.get('id')
    if not exam_session_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam session ID is required.'
        })
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
    except ExamSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam session not found.'
        })
    
    # Check if exam session can be edited (not published or verified)
    if exam_session.status in ['published', 'verified']:
        return JsonResponse({
            'success': False,
            'message': f'Cannot edit a {exam_session.get_status_display().lower()} exam session.'
        })
    
    # Get and validate required fields
    name = request.POST.get('name', '').strip()
    exam_type_id = request.POST.get('exam_type')
    academic_year_id = request.POST.get('academic_year')
    term_id = request.POST.get('term')
    class_level_id = request.POST.get('class_level')
    exam_date_str = request.POST.get('exam_date')
    
    if not all([name, exam_type_id, academic_year_id, term_id, class_level_id, exam_date_str]):
        return JsonResponse({
            'success': False,
            'message': 'All required fields must be filled.'
        })
    
    # Parse exam date
    try:
        exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid exam date format.'
        })
    
    # Get optional fields
    stream_class_id = request.POST.get('stream_class', '').strip()
    stream_class = None
    if stream_class_id:
        try:
            stream_class = StreamClass.objects.get(id=stream_class_id)
        except StreamClass.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected stream class does not exist.'
            })
    
    # Validate name length
    if len(name) < 5 or len(name) > 200:
        return JsonResponse({
            'success': False,
            'message': 'Exam session name must be between 5 and 200 characters.'
        })
    
    # Get related objects
    try:
        exam_type = ExamType.objects.get(id=exam_type_id)
        academic_year = AcademicYear.objects.get(id=academic_year_id)
        term = Term.objects.get(id=term_id)
        class_level = ClassLevel.objects.get(id=class_level_id)
    except (ExamType.DoesNotExist, AcademicYear.DoesNotExist, 
            Term.DoesNotExist, ClassLevel.DoesNotExist) as e:
        return JsonResponse({
            'success': False,
            'message': f'Selected item does not exist: {str(e)}'
        })
    
    # Check for duplicate exam session name (excluding current)
    duplicate_check = ExamSession.objects.filter(
        name__iexact=name,
        academic_year=academic_year,
        term=term,
        class_level=class_level
    ).exclude(id=exam_session.id)
    
    if stream_class:
        duplicate_check = duplicate_check.filter(stream_class=stream_class)
    else:
        duplicate_check = duplicate_check.filter(stream_class__isnull=True)
    
    if duplicate_check.exists():
        return JsonResponse({
            'success': False,
            'message': f'Another exam session with name "{name}" already exists for the selected parameters.'
        })
    
    try:
        # Update the exam session
        exam_session.name = name
        exam_session.exam_type = exam_type
        exam_session.academic_year = academic_year
        exam_session.term = term
        exam_session.class_level = class_level
        exam_session.stream_class = stream_class
        exam_session.exam_date = exam_date
        exam_session.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Exam session "{name}" updated successfully.',
            'exam_session': {
                'id': exam_session.id,
                'name': exam_session.name,
                'exam_type_name': exam_session.exam_type.name,
                'academic_year_name': exam_session.academic_year.name,
                'term_name': f'{exam_session.term.get_term_number_display()}',
                'class_level_name': exam_session.class_level.name,
                'stream_class_name': str(exam_session.stream_class) if exam_session.stream_class else 'All Streams',
                'exam_date': exam_session.exam_date.strftime('%Y-%m-%d'),
                'status': exam_session.status,
                'status_display': exam_session.get_status_display()
            }
        })
        
    except IntegrityError as e:
        return JsonResponse({
            'success': False,
            'message': f'Database error: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating exam session: {str(e)}'
        })

def toggle_exam_session_status(request):
    """Toggle exam session status through workflow"""
    exam_session_id = request.POST.get('id')
    new_status = request.POST.get('status', '').lower()
    
    if not exam_session_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam session ID is required.'
        })
    
    valid_statuses = ['draft', 'submitted', 'verified', 'published']
    if new_status not in valid_statuses:
        return JsonResponse({
            'success': False,
            'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        })
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
    except ExamSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam session not found.'
        })
    
    # Validate status transition
    current_status = exam_session.status
    allowed_transitions = {
        'draft': ['submitted', 'draft'],
        'submitted': ['verified', 'draft'],
        'verified': ['published', 'submitted'],
        'published': ['published']  # Once published, cannot change
    }
    
    if new_status not in allowed_transitions.get(current_status, []):
        return JsonResponse({
            'success': False,
            'message': f'Cannot change status from {current_status} to {new_status}.'
        })
    
    # Additional validation for publishing
    if new_status == 'published':
        # Check if exam date is in the past
        if exam_session.exam_date > date.today():
            return JsonResponse({
                'success': False,
                'message': 'Cannot publish an exam session with future date.'
            })
        
        # Check if there are papers added
        if not exam_session.results.exists():
            return JsonResponse({
                'success': False,
                'message': 'Cannot publish an exam session without any papers.'
            })
    
    try:
        # Update status
        exam_session.status = new_status
        exam_session.save()
        
        action_text = {
            'draft': 'returned to draft',
            'submitted': 'submitted for review',
            'verified': 'verified',
            'published': 'published'
        }.get(new_status, 'updated')
        
        return JsonResponse({
            'success': True,
            'message': f'Exam session "{exam_session.name}" {action_text} successfully.',
            'status': exam_session.status,
            'status_display': exam_session.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        })

def delete_exam_session(request):
    """Delete an exam session"""
    exam_session_id = request.POST.get('id')
    if not exam_session_id:
        return JsonResponse({
            'success': False,
            'message': 'Exam session ID is required.'
        })
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
    except ExamSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam session not found.'
        })
    
    # Check if exam session can be deleted
    if exam_session.status in ['published', 'verified']:
        return JsonResponse({
            'success': False,
            'message': f'Cannot delete a {exam_session.get_status_display().lower()} exam session.'
        })
    
    # Check if there are any papers or results
    if exam_session.results.exists():
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete exam session with papers. Delete papers first.'
        })
    
    exam_session_name = exam_session.name
    
    try:
        exam_session.delete()
        return JsonResponse({
            'success': True,
            'message': f'Exam session "{exam_session_name}" deleted successfully.',
            'id': exam_session_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting exam session: {str(e)}'
        })

def update_exam_session_status(request):
    """Update exam session status with custom message"""
    exam_session_id = request.POST.get('id')
    status = request.POST.get('status', '').lower()
    
    if not exam_session_id or not status:
        return JsonResponse({
            'success': False,
            'message': 'Exam session ID and status are required.'
        })
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
    except ExamSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam session not found.'
        })
    
    # Validate status
    valid_statuses = [choice[0] for choice in ExamSession.STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({
            'success': False,
            'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        })
    
    try:
        old_status = exam_session.status
        exam_session.status = status
        exam_session.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Exam session status changed from {old_status} to {status}.',
            'status': exam_session.status,
            'status_display': exam_session.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        })

@login_required
def exam_session_detail(request, exam_session_id):
    """View exam session details"""
    exam_session = get_object_or_404(
        ExamSession.objects.select_related(
            'exam_type',
            'academic_year',
            'term',
            'class_level',
            'class_level__educational_level',
            'stream_class'
        ),
        id=exam_session_id
    )
    
    # Get papers for this exam session
    papers = exam_session.papers.select_related('subject').all()
    
    # Get student count for this class/stream
    if exam_session.stream_class:
        student_count = Student.objects.filter(
            class_level=exam_session.class_level,
            stream_class=exam_session.stream_class,
            is_active=True
        ).count()
    else:
        student_count = Student.objects.filter(
            class_level=exam_session.class_level,
            is_active=True
        ).count()
    
    # Get statistics
    total_papers = papers.count()
    papers_with_results = papers.filter(results__isnull=False).distinct().count()
    
    context = {
        'exam_session': exam_session,
        'papers': papers,
        'student_count': student_count,
        'total_papers': total_papers,
        'papers_with_results': papers_with_results,
        'page_title': f'Exam Session: {exam_session.name}',
    }
    
    return render(request, 'admin/results/exam_session_detail.html', context)



@login_required
def get_streams_for_exam_session(request):
    """AJAX endpoint to get streams for a class level in exam session"""
    class_level_id = request.GET.get('class_level_id')
    
    if not class_level_id:
        return JsonResponse({'success': False, 'message': 'Class level ID required'})
    
    try:
        streams = StreamClass.objects.filter(
            class_level_id=class_level_id,
            is_active=True
        ).select_related('class_level').order_by('stream_letter')
        
        stream_list = [{'id': '', 'text': 'All Streams'}]  # Add option for all streams
        for stream in streams:
            stream_list.append({
                'id': stream.id,
                'text': f"{stream.class_level.name}{stream.stream_letter}"
            })
        
        return JsonResponse({
            'success': True,
            'streams': stream_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def get_exam_session_stats(request):
    """AJAX endpoint to get exam session statistics"""
    exam_session_id = request.GET.get('exam_session_id')
    
    if not exam_session_id:
        return JsonResponse({'success': False, 'message': 'Exam session ID required'})
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
        
        # Get paper count
        paper_count = exam_session.papers.count()
        
        # Get student count
        if exam_session.stream_class:
            student_count = Student.objects.filter(
                class_level=exam_session.class_level,
                stream_class=exam_session.stream_class,
                is_active=True
            ).count()
        else:
            student_count = Student.objects.filter(
                class_level=exam_session.class_level,
                is_active=True
            ).count()
        
        # Get result statistics
        result_stats = StudentResult.objects.filter(
            exam_paper__exam_session=exam_session
        ).aggregate(
            total_students=Count('student', distinct=True),
            papers_marked=Count('exam_paper', distinct=True),
            average_percentage=Avg('percentage'),
            highest_percentage=Max('percentage'),
            lowest_percentage=Min('percentage')
        )
        
        return JsonResponse({
            'success': True,
            'stats': {
                'paper_count': paper_count,
                'student_count': student_count,
                **result_stats
            }
        })
    except ExamSession.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Exam session not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})        
    
def admin_exam_sessions_data(request):
    """Return exam sessions data as JSON for DataTable"""
    try:
        # Get DataTable parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        # Get filter parameters
        academic_year = request.GET.get('academic_year')
        term = request.GET.get('term')
        class_level = request.GET.get('class_level')
        stream = request.GET.get('stream')
        status = request.GET.get('status')
        
        # Log the filters for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Filters - Academic Year: {academic_year}, Term: {term}, Class Level: {class_level}, Stream: {stream}, Status: {status}")
        
        # Build base queryset
        queryset = ExamSession.objects.select_related(
            'exam_type', 'academic_year', 'term', 
            'class_level', 'stream_class'
        ).order_by('-exam_date')
        
        # Apply filters
        if academic_year:
            queryset = queryset.filter(academic_year_id=academic_year)
        if term:
            queryset = queryset.filter(term_id=term)
        if class_level:
            queryset = queryset.filter(class_level_id=class_level)
        if stream:
            queryset = queryset.filter(stream_class_id=stream)
        if status:
            queryset = queryset.filter(status=status)
        
        # Apply search
        if search_value:
            queryset = queryset.filter(
                Q(name__icontains=search_value) |
                Q(exam_type__name__icontains=search_value) |
                Q(academic_year__name__icontains=search_value) |
                Q(class_level__name__icontains=search_value)
            )
        
        # Get total count
        total_records = queryset.count()
        logger.debug(f"Total records found: {total_records}")
        
        # If no records, return empty response immediately
        if total_records == 0:
            return JsonResponse({
                'draw': draw,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': []
            })
        
        # Paginate
        paginator = Paginator(queryset, length)
        page_number = (start // length) + 1
        try:
            page_obj = paginator.get_page(page_number)
        except EmptyPage:
            # If page is out of range, return empty results
            return JsonResponse({
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': total_records,
                'data': []
            })
        
        # Prepare data
        data = []
        today = date.today()
        
        for session in page_obj:
            # Determine exam date status
            if session.exam_date < today:
                exam_date_status = 'past'
            elif session.exam_date == today:
                exam_date_status = 'today'
            else:
                exam_date_status = 'future'
            
            data.append({
                'id': session.id,
                'name': session.name,
                'exam_type': session.exam_type.id,
                'exam_type_name': session.exam_type.name,
                'academic_year': session.academic_year.id,
                'academic_year_name': session.academic_year.name,
                'term': session.term.id,
                'term_display': session.term.get_term_number_display(),
                'class_level': session.class_level.id,
                'class_level_name': session.class_level.name,
                'stream_class': session.stream_class.id if session.stream_class else None,
                'stream_class_stream_letter': session.stream_class.stream_letter if session.stream_class else None,
                'exam_date': session.exam_date.isoformat(),
                'exam_date_formatted': session.exam_date.strftime('%Y-%m-%d'),
                'exam_date_status': exam_date_status,
                'status': session.status,
                'status_display': session.get_status_display(),
                'created_at': session.created_at.isoformat(),
                'created_at_formatted': session.created_at.strftime('%Y-%m-%d'),
                'created_at_relative': timesince(session.created_at),
            })
        
        logger.debug(f"Returning {len(data)} records")
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': data
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in admin_exam_sessions_data: {str(e)}")
        return JsonResponse({
            'draw': 1,
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }, status=500)


@login_required
def get_exam_session_by_id(request):
    """Get single exam session data for editing"""
    try:
        exam_session_id = request.GET.get('exam_session_id')
        if not exam_session_id:
            return JsonResponse({
                'success': False,
                'message': 'Exam session ID is required.'
            })
        
        session = ExamSession.objects.select_related(
            'exam_type', 'academic_year', 'term', 
            'class_level', 'stream_class'
        ).get(id=exam_session_id)
        
        data = {
            'id': session.id,
            'name': session.name,
            'exam_type': session.exam_type.id,
            'exam_type_name': session.exam_type.name,
            'academic_year': session.academic_year.id,
            'academic_year_name': session.academic_year.name,
            'term': session.term.id,
            'term_name': session.term.get_term_number_display(),
            'class_level': session.class_level.id,
            'class_level_name': session.class_level.name,
            'stream_class': session.stream_class.id if session.stream_class else '',
            'stream_class_name': str(session.stream_class) if session.stream_class else '',
            'exam_date': session.exam_date.strftime('%Y-%m-%d'),
            'status': session.status,
            'status_display': session.get_status_display(),
        }
        
        return JsonResponse({
            'success': True,
            'exam_session': data
        })
    except ExamSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Exam session not found.'
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_exam_session_by_id: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error loading exam session: {str(e)}'
        })




@login_required
def manage_results(request, exam_session_id):
    exam_session = get_object_or_404(
        ExamSession.objects.select_related(
            'exam_type',
            'academic_year',
            'term',
            'class_level',
            'class_level__educational_level',
            'stream_class'
        ),
        id=exam_session_id
    )

    subjects = Subject.objects.filter(
        educational_level=exam_session.class_level.educational_level,
        is_active=True
    ).order_by('code')

    if exam_session.stream_class:
        students = Student.objects.filter(
            class_level=exam_session.class_level,
            stream_class=exam_session.stream_class,
            is_active=True
        )
    else:
        students = Student.objects.filter(
            class_level=exam_session.class_level,
            is_active=True
        )

    students = students.order_by('first_name')

    results = StudentResult.objects.filter(
        exam_session=exam_session
    ).select_related('student', 'subject')

    student_results_data = []

    for student in students:
        student_results = results.filter(student=student)

        subject_results = {}
        total_subjects = 0

        for subject in subjects:
            result = student_results.filter(subject=subject).first()

            if result:
                subject_results[subject.id] = {
                    'marks': result.marks_obtained,
                    'grade': result.grade,
                    'grade_point': result.grade_point,
                    'position': result.position_in_paper,
                    'result_id': result.id
                }
                if result.marks_obtained is not None:
                    total_subjects += 1
            else:
                subject_results[subject.id] = {
                    'marks': None,
                    'grade': '',
                    'grade_point': None,
                    'position': None,
                    'result_id': None
                }

        # 🔹 Pull pre-calculated exam metrics
        try:
            metrics = StudentExamMetrics.objects.get(
                student=student,
                exam_session=exam_session
            )
        except StudentExamMetrics.DoesNotExist:
            metrics = None

        # 🔹 Pull pre-calculated positions
        try:
            position = StudentExamPosition.objects.get(
                student=student,
                exam_session=exam_session
            )
        except StudentExamPosition.DoesNotExist:
            position = None

        student_results_data.append({
            'student': student,
            'student_id': student.id,
            'registration_number': student.registration_number or f"S{student.id:04d}",
            'full_name': student.full_name,
            'gender': student.get_gender_display(),

            # Metrics (already computed elsewhere)
            'total_marks': metrics.total_marks if metrics else None,
            'average_marks': metrics.average_marks if metrics else None,
            'average_percentage': metrics.average_percentage if metrics else None,
            'average_grade': metrics.average_grade if metrics else '',
            'average_remark': metrics.average_remark if metrics else '',
            'total_grade_points': metrics.total_grade_points if metrics else None,
            'division': metrics.division if metrics else '',

            # Positions
            'class_position': position.class_position if position else None,
            'stream_position': position.stream_position if position else None,

            'subject_results': subject_results,
            'has_results': total_subjects > 0
        })

    context = {
        'exam_session': exam_session,
        'subjects': subjects,
        'students': students,
        'student_results_data': student_results_data,
        'page_title': f'Manage Results - {exam_session.name}',
    }

    return render(request, 'admin/results/manage_results.html', context)



@login_required
@require_POST
def save_student_results(request):
    """Save multiple student results with strict marks validation (0–100 or empty)"""

    try:
        data = json.loads(request.body)

        exam_session_id = data.get('exam_session_id')
        results_data = data.get('results', [])
        is_auto_save = data.get('is_auto_save', False)

        if not exam_session_id or not isinstance(results_data, list):
            return JsonResponse({
                'success': False,
                'message': 'Invalid data provided.'
            }, status=400)

        exam_session = get_object_or_404(ExamSession, id=exam_session_id)

        saved_results = []
        saved_count = 0
        skipped_count = 0

        with transaction.atomic():
            for result_data in results_data:
                student_id = result_data.get('student_id')
                subject_id = result_data.get('subject_id')
                marks_obtained = result_data.get('marks_obtained')

                # Required IDs
                if not student_id or not subject_id:
                    skipped_count += 1
                    continue

                # Allow empty marks (skip save)
                if marks_obtained in ("", None):
                    skipped_count += 1
                    continue

                # Ensure numeric (use Decimal to match model DecimalFields)
                try:
                    marks_obtained = Decimal(str(marks_obtained))
                except (TypeError, ValueError, InvalidOperation):
                    skipped_count += 1
                    continue

                # Enforce range 0–100
                if marks_obtained < 0 or marks_obtained > 100:
                    skipped_count += 1
                    continue

                # Save or update result
                result, created = StudentResult.objects.get_or_create(
                    exam_session=exam_session,
                    student_id=student_id,
                    subject_id=subject_id,
                    defaults={'marks_obtained': marks_obtained}
                )

                if not created:
                    result.marks_obtained = marks_obtained

                # Percentage (use Decimal arithmetic)
                max_score = exam_session.exam_type.max_score
                if max_score and max_score > 0:
                    try:
                        max_score_decimal = Decimal(str(max_score))
                        result.percentage = (marks_obtained / max_score_decimal) * Decimal('100')
                    except (InvalidOperation, TypeError):
                        result.percentage = None

                # Grade calculation
                education_level = exam_session.class_level.educational_level
                grade_scale = GradingScale.objects.filter(
                    education_level=education_level,
                    min_mark__lte=marks_obtained,
                    max_mark__gte=marks_obtained
                ).first()

                if grade_scale:
                    result.grade = grade_scale.grade
                    result.grade_point = grade_scale.points
                else:
                    result.grade = None
                    result.grade_point = None

                result.save()

                saved_results.append({
                    'student_id': student_id,
                    'subject_id': subject_id,
                    'result_id': result.id
                })

                saved_count += 1

        # Calculate positions only for manual save
        if saved_count > 0 and not is_auto_save:
            calculate_subject_positions(exam_session)

        return JsonResponse({
            'success': True,
            'message': f'Saved {saved_count} results. Skipped {skipped_count}.',
            'saved_count': saved_count,
            'skipped_count': skipped_count,
            'saved_results': saved_results
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON payload.'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving results: {str(e)}'
        }, status=500)



@login_required
@require_POST
def save_multiple_results(request):
    """Save multiple new results from modal with marks validation (0–100 or empty)"""

    try:
        exam_session_id = request.POST.get('exam_session_id')
        results_json = request.POST.get('results')

        if not exam_session_id or not results_json:
            return JsonResponse({
                'success': False,
                'message': 'Invalid data provided.'
            }, status=400)

        try:
            results_data = json.loads(results_json)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid results JSON.'
            }, status=400)

        exam_session = get_object_or_404(ExamSession, id=exam_session_id)

        saved_count = 0
        skipped_count = 0
        errors = []

        with transaction.atomic():
            for result_data in results_data:
                student_id = result_data.get('studentId')
                subject_id = result_data.get('subjectId')
                marks = result_data.get('marks')

                # Validate IDs
                if not student_id or not subject_id:
                    skipped_count += 1
                    continue

                # Allow empty marks → skip
                if marks in ("", None):
                    skipped_count += 1
                    continue

                # Ensure numeric marks (use Decimal)
                try:
                    marks = Decimal(str(marks))
                except (TypeError, ValueError, InvalidOperation):
                    errors.append(
                        f"Invalid marks for student {student_id}, subject {subject_id}"
                    )
                    continue

                # Enforce range 0–100
                if marks < 0 or marks > 100:
                    errors.append(
                        f"Marks out of range (0–100) for student {student_id}, subject {subject_id}"
                    )
                    continue

                # Prevent duplicate result
                if StudentResult.objects.filter(
                    exam_session=exam_session,
                    student_id=student_id,
                    subject_id=subject_id
                ).exists():
                    errors.append(
                        f"Result already exists for student {student_id}, subject {subject_id}"
                    )
                    continue

                # Create result
                result = StudentResult.objects.create(
                    exam_session=exam_session,
                    student_id=student_id,
                    subject_id=subject_id,
                    marks_obtained=marks
                )

                # Percentage (use Decimal arithmetic)
                max_score = exam_session.exam_type.max_score
                if max_score and max_score > 0:
                    try:
                        max_score_decimal = Decimal(str(max_score))
                        result.percentage = (marks / max_score_decimal) * Decimal('100')
                    except (InvalidOperation, TypeError):
                        result.percentage = None

                # Grade
                education_level = exam_session.class_level.educational_level
                grade_scale = GradingScale.objects.filter(
                    education_level=education_level,
                    min_mark__lte=marks,
                    max_mark__gte=marks
                ).first()

                if grade_scale:
                    result.grade = grade_scale.grade
                    result.grade_point = grade_scale.points

                result.save()
                saved_count += 1

        # Calculate positions only if something was saved
        if saved_count > 0:
            calculate_subject_positions(exam_session)

        response_data = {
            'success': True,
            'message': f'Saved {saved_count} results. Skipped {skipped_count}.',
            'saved_count': saved_count,
            'skipped_count': skipped_count
        }

        if errors:
            response_data['errors'] = errors[:5]  # limit noise

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving results: {str(e)}'
        }, status=500)

def calculate_subject_positions(exam_session):
    """Calculate positions for all subjects in an exam session"""
    try:
        # Get all subjects in this exam session
        subjects = Subject.objects.filter(
            educational_level=exam_session.class_level.educational_level,
            is_active=True
        )
        
        for subject in subjects:
            calculate_subject_position(exam_session, subject)
            
    except Exception as e:
        print(f"Error calculating positions: {str(e)}")

def calculate_subject_position(exam_session, subject):
    """Calculate positions for a specific subject"""
    try:
        # Get all results for this subject ordered by marks (descending)
        results = StudentResult.objects.filter(
            exam_session=exam_session,
            subject=subject,
            marks_obtained__isnull=False
        ).select_related('student').order_by('-marks_obtained')
        
        position = 1
        previous_marks = None
        skip_position = 0
        
        for index, result in enumerate(results):
            current_marks = result.marks_obtained
            
            # Handle equal marks (same position)
            if previous_marks is not None and current_marks == previous_marks:
                # Same position as previous student
                result.position_in_paper = position - 1
                skip_position += 1
            else:
                # New position
                result.position_in_paper = position
                position += 1 + skip_position
                skip_position = 0
            
            result.save(update_fields=['position_in_paper'])
            previous_marks = current_marks
            
    except Exception as e:
        print(f"Error calculating position for subject {subject.id}: {str(e)}")

@login_required
def subject_results_entry(request, exam_session_id, subject_id):
    """Entry page for entering marks for all students in a specific subject"""
    exam_session = get_object_or_404(
        ExamSession.objects.select_related(
            'exam_type',
            'academic_year',
            'term',
            'class_level',
            'class_level__educational_level',
            'stream_class'
        ),
        id=exam_session_id
    )
    
    subject = get_object_or_404(Subject, id=subject_id)
    
    # Get students based on stream
    if exam_session.stream_class:
        students = Student.objects.filter(
            class_level=exam_session.class_level,
            stream_class=exam_session.stream_class,
            is_active=True
        )
    else:
        students = Student.objects.filter(
            class_level=exam_session.class_level,
            is_active=True
        )
    
    students = students.order_by('first_name', 'last_name')
    
    # Get existing results for this subject
    existing_results = StudentResult.objects.filter(
        exam_session=exam_session,
        subject=subject
    ).select_related('student')
    
    # Create a dictionary of existing results for quick lookup
    results_dict = {result.student_id: result for result in existing_results}
    
    # Prepare student data with existing marks
    students_data = []
    for student in students:
        result = results_dict.get(student.id)
        students_data.append({
            'id': student.id,
            'registration_number': student.registration_number or f"S{student.id:04d}",
            'full_name': student.full_name,
            'gender': student.get_gender_display(),
            'existing_marks': result.marks_obtained if result else None,
            'existing_grade': result.grade if result else '',
            'result_id': result.id if result else None,
            'has_result': bool(result)
        })
    
    # Get statistics
    total_students = students.count()
    with_marks = len([s for s in students_data if s['existing_marks'] is not None])
    without_marks = total_students - with_marks
    
    context = {
        'exam_session': exam_session,
        'subject': subject,
        'students_data': students_data,
        'total_students': total_students,
        'with_marks': with_marks,
        'without_marks': without_marks,
        'progress_percentage': (with_marks / total_students * 100) if total_students > 0 else 0,
        'page_title': f'Enter Marks - {subject.name}',
    }
    
    return render(request, 'admin/results/subject_results_entry.html', context)        




@login_required
def download_excel_template(request, exam_session_id, subject_id):
    """Generate and download Excel template for marks entry"""
    try:
        exam_session = get_object_or_404(
            ExamSession.objects.select_related(
                'exam_type', 'class_level', 'stream_class',
                'academic_year', 'term'
            ),
            id=exam_session_id
        )
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Get students for this exam session
        if exam_session.stream_class:
            students = Student.objects.filter(
                class_level=exam_session.class_level,
                stream_class=exam_session.stream_class,
                is_active=True
            )
        else:
            students = Student.objects.filter(
                class_level=exam_session.class_level,
                is_active=True
            )
        
        students = students.order_by('first_name', 'last_name')
        
        # Get existing results
        existing_results = StudentResult.objects.filter(
            exam_session=exam_session,
            subject=subject
        )
        results_dict = {r.student_id: r.marks_obtained for r in existing_results}
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Marks Entry"
        
        # Define styles
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        info_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        info_font = Font(name="Arial", size=10, bold=True)
        
        cell_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        
        # Add header information
        ws['A1'] = "MARKS ENTRY TEMPLATE"
        ws['A1'].font = Font(name="Arial", size=14, bold=True)
        ws['A1'].alignment = center_alignment
        ws.merge_cells('A1:D1')
        
        ws['A2'] = f"Exam Session: {exam_session.name}"
        ws['A2'].font = info_font
        ws.merge_cells('A2:D2')
        
        ws['A3'] = f"Subject: {subject.name} ({subject.code})"
        ws['A3'].font = info_font
        ws.merge_cells('A3:D3')
        
        ws['A4'] = f"Class: {exam_session.class_level.name}"
        if exam_session.stream_class:
            ws['A4'] += f" {exam_session.stream_class.stream_letter}"
        ws['A4'].font = info_font
        ws.merge_cells('A4:D4')
        
        ws['A5'] = f"Academic Year: {exam_session.academic_year.name}"
        ws['A5'].font = info_font
        ws.merge_cells('A5:D5')
        
        ws['A6'] = f"Term: {exam_session.term.get_term_number_display()}"
        ws['A6'].font = info_font
        ws.merge_cells('A6:D6')
        
        ws['A7'] = f"Maximum Score: {exam_session.exam_type.max_score}"
        ws['A7'].font = info_font
        ws.merge_cells('A7:D7')
        
        # Add instruction rows
        ws['A9'] = "INSTRUCTIONS:"
        ws['A9'].font = Font(name="Arial", size=11, bold=True, color="FF0000")
        ws.merge_cells('A9:D9')
        
        instructions = [
            "1. Fill marks in the 'Marks' column (Column D).",
            "2. Leave blank for absent students.",
            "3. Enter 0 for zero marks (it's a valid mark).",
            "4. Do not modify Student ID, Registration No., or Student Name columns.",
            f"5. Marks range: 0 - {exam_session.exam_type.max_score}",
            "6. Save file and upload using the upload feature."
        ]
        
        for i, instruction in enumerate(instructions, start=10):
            cell = ws[f'A{i}']
            cell.value = instruction
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(wrap_text=True)
            ws.merge_cells(f'A{i}:D{i}')
        
        # Add headers for data
        header_row = 16
        headers = ["Student ID", "Registration No.", "Student Name", "Marks"]
        
        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            ws.column_dimensions[get_column_letter(col_num)].width = 20
        
        # Add student data
        data_start_row = header_row + 1
        
        for i, student in enumerate(students, start=data_start_row):
            # Student ID
            ws.cell(row=i, column=1, value=student.id)
            ws.cell(row=i, column=1).border = cell_border
            ws.cell(row=i, column=1).alignment = center_alignment
            
            # Registration Number
            ws.cell(row=i, column=2, value=student.registration_number or f"S{student.id:04d}")
            ws.cell(row=i, column=2).border = cell_border
            ws.cell(row=i, column=2).alignment = left_alignment
            
            # Student Name
            ws.cell(row=i, column=3, value=student.full_name)
            ws.cell(row=i, column=3).border = cell_border
            ws.cell(row=i, column=3).alignment = left_alignment
            
            # Marks (pre-filled if exists)
            existing_marks = results_dict.get(student.id)
            ws.cell(row=i, column=4, value=existing_marks)
            ws.cell(row=i, column=4).border = cell_border
            ws.cell(row=i, column=4).alignment = center_alignment
            
            # Add data validation for marks
            if exam_session.exam_type.max_score:
                dv = openpyxl.worksheet.datavalidation.DataValidation(
                    type="decimal",
                    operator="between",
                    formula1=0,
                    formula2=exam_session.exam_type.max_score,
                    allow_blank=True,
                    showErrorMessage=True,
                    errorTitle="Invalid Marks",
                    error="Marks must be between 0 and " + str(exam_session.exam_type.max_score)
                )
                ws.add_data_validation(dv)
                dv.add(f'D{i}:D{i}')
        
        # Add summary row
        summary_row = data_start_row + len(students) + 2
        ws.cell(row=summary_row, column=1, value="Summary:")
        ws.cell(row=summary_row, column=1).font = Font(bold=True)
        
        ws.cell(row=summary_row + 1, column=1, value="Total Students:")
        ws.cell(row=summary_row + 1, column=2, value=len(students))
        ws.cell(row=summary_row + 1, column=2).font = Font(bold=True)
        
        ws.cell(row=summary_row + 2, column=1, value="With Existing Marks:")
        ws.cell(row=summary_row + 2, column=2, 
                value=f"=COUNTIF(D{data_start_row}:D{data_start_row + len(students) - 1},\"<>\"&\"\")")
        ws.cell(row=summary_row + 2, column=2).font = Font(bold=True)
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Marks_Template_{subject.code}_{exam_session.name.replace(' ', '_')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Save workbook to response
        wb.save(response)
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating template: {str(e)}")
        return redirect('manage_results', exam_session_id=exam_session_id)

@login_required
@require_POST
def upload_excel_marks(request):
    """Handle Excel file upload for bulk marks entry"""
    try:
        excel_file = request.FILES.get('excel_file')
        exam_session_id = request.POST.get('exam_session_id')
        subject_id = request.POST.get('subject_id')
        
        if not excel_file:
            return JsonResponse({
                'success': False,
                'message': 'No file uploaded'
            })
        
        if not exam_session_id or not subject_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing exam session or subject ID'
            })
        
        exam_session = get_object_or_404(ExamSession, id=exam_session_id)
        subject = get_object_or_404(Subject, id=subject_id)
        
        # Read Excel file
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        ws = wb.active
        
        # Parse data
        data = []
        errors = []
        processed_count = 0
        
        # Find header row
        header_row = None
        for row in ws.iter_rows(min_row=1, max_row=20, values_only=True):
            if row and row[0] and isinstance(row[0], str) and "Student ID" in str(row[0]):
                header_row = row
                break
        
        if not header_row:
            return JsonResponse({
                'success': False,
                'message': 'Could not find header row in Excel file'
            })
        
        # Find start of data
        data_start_row = None
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=100, values_only=True), start=1):
            if row and isinstance(row[0], (int, float)):
                data_start_row = i
                break
        
        if not data_start_row:
            return JsonResponse({
                'success': False,
                'message': 'No data found in Excel file'
            })
        
        # Process each row
        for i, row in enumerate(ws.iter_rows(min_row=data_start_row, max_row=ws.max_row, values_only=True), start=data_start_row):
            if not row or not row[0]:
                continue
            
            try:
                student_id = int(row[0])
                marks = row[3] if len(row) > 3 else None
                
                # Validate student exists
                try:
                    student = Student.objects.get(id=student_id, is_active=True)
                except Student.DoesNotExist:
                    errors.append(f"Row {i}: Student ID {student_id} not found")
                    continue
                
                # Validate marks
                if marks is not None and marks != '':
                    try:
                        marks = Decimal(str(marks))
                        max_score = exam_session.exam_type.max_score
                        
                        if marks < 0 or marks > max_score:
                            errors.append(f"Row {i}: Marks {marks} out of range (0-{max_score})")
                            continue
                    except (ValueError, InvalidOperation):
                        errors.append(f"Row {i}: Invalid marks format '{marks}'")
                        continue
                else:
                    marks = None
                
                data.append({
                    'student_id': student_id,
                    'marks': marks
                })
                
            except Exception as e:
                errors.append(f"Row {i}: Error processing row - {str(e)}")
        
        # Save marks in transaction
        with transaction.atomic():
            for item in data:
                try:
                    # Get or create result
                    result, created = StudentResult.objects.get_or_create(
                        exam_session=exam_session,
                        student_id=item['student_id'],
                        subject=subject,
                        defaults={'marks_obtained': item['marks']}
                    )
                    
                    if not created:
                        result.marks_obtained = item['marks']
                    
                    # Calculate percentage
                    if item['marks'] is not None and exam_session.exam_type.max_score > 0:
                        result.percentage = (Decimal(str(item['marks'])) / 
                                           Decimal(str(exam_session.exam_type.max_score))) * Decimal('100')
                    
                    # Calculate grade
                    if item['marks'] is not None:
                        education_level = exam_session.class_level.educational_level
                        grade_scale = GradingScale.objects.filter(
                            education_level=education_level,
                            min_mark__lte=item['marks'],
                            max_mark__gte=item['marks']
                        ).first()
                        
                        if grade_scale:
                            result.grade = grade_scale.grade
                            result.grade_point = grade_scale.points
                    
                    result.save()
                    processed_count += 1
                    
                except Exception as e:
                    errors.append(f"Student ID {item['student_id']}: Error saving - {str(e)}")
        
        # Calculate positions after upload
        calculate_subject_positions(exam_session)
        
        response_data = {
            'success': True,
            'message': f'Successfully processed {processed_count} marks',
            'processed_count': processed_count,
            'total_rows': len(data)
        }
        
        if errors:
            response_data['errors'] = errors[:10]  # Limit errors to first 10
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error processing file: {str(e)}'
        })




@login_required
def download_pdf_report(request, exam_session_id, subject_id):
    """Generate and download PDF report with gender + subject performance analytics"""
    try:
        # ==================================================
        # 1. LOAD CORE OBJECTS
        # ==================================================
        exam_session = get_object_or_404(
            ExamSession.objects.select_related(
                'exam_type',
                'class_level',
                'stream_class',
                'academic_year',
                'term',
                'class_level__educational_level'
            ),
            id=exam_session_id
        )

        subject = get_object_or_404(Subject, id=subject_id)

        # ==================================================
        # 2. LOAD STUDENTS
        # ==================================================
        student_filters = {
            'class_level': exam_session.class_level,
            'is_active': True
        }

        if exam_session.stream_class:
            student_filters['stream_class'] = exam_session.stream_class

        students = Student.objects.filter(**student_filters).order_by(
            'first_name', 'last_name'
        )

        # ==================================================
        # 3. LOAD RESULTS (THIS SUBJECT)
        # ==================================================
        results = StudentResult.objects.filter(
            exam_session=exam_session,
            subject=subject
        ).select_related('student')

        results_by_student = {r.student_id: r for r in results}

        # ==================================================
        # 4. PREPARE STUDENT DATA + GENDER STATS
        # ==================================================
        students_data = []
        total_marks = 0
        students_with_marks = 0

        gender_totals = {}
        gender_marks_sum = {}
        gender_with_marks = {}

        for student in students:
            result = results_by_student.get(student.id)
            marks = result.marks_obtained if result else None
            grade = ''

            gender = student.get_gender_display() or 'Unknown'

            gender_totals.setdefault(gender, 0)
            gender_marks_sum.setdefault(gender, 0)
            gender_with_marks.setdefault(gender, 0)

            gender_totals[gender] += 1

            if marks is not None:
                total_marks += marks
                students_with_marks += 1

                gender_marks_sum[gender] += marks
                gender_with_marks[gender] += 1

                grade_scale = GradingScale.objects.filter(
                    education_level=exam_session.class_level.educational_level,
                    min_mark__lte=marks,
                    max_mark__gte=marks
                ).first()

                if grade_scale:
                    grade = grade_scale.grade

            students_data.append({
                'reg_number': student.registration_number or f"S{student.id:04d}",
                'name': student.full_name,
                'gender': gender,
                'marks': marks,
                'grade': grade,
                'has_marks': marks is not None
            })

        # ==================================================
        # 5. OVERALL STATISTICS
        # ==================================================
        statistics = {
            'total_students': students.count(),
            'students_with_marks': students_with_marks,
            'students_without_marks': students.count() - students_with_marks,
            'percentage_completed': (
                (students_with_marks / students.count()) * 100
                if students.exists() else 0
            ),
            'average_marks': (
                total_marks / students_with_marks
                if students_with_marks > 0 else 0
            ),
            'highest_marks': max(
                [s['marks'] for s in students_data if s['marks'] is not None],
                default=0
            ),
            'lowest_marks': min(
                [s['marks'] for s in students_data if s['marks'] is not None],
                default=0
            ),
        }

        # ==================================================
        # 6. GRADE DISTRIBUTION
        # ==================================================
        grade_distribution = {}
        for s in students_data:
            if s['grade']:
                grade_distribution[s['grade']] = (
                    grade_distribution.get(s['grade'], 0) + 1
                )

        # ==================================================
        # 7. GENDER STATISTICS
        # ==================================================
        gender_statistics = []

        for gender, total in gender_totals.items():
            with_marks = gender_with_marks.get(gender, 0)
            avg = (
                gender_marks_sum[gender] / with_marks
                if with_marks > 0 else 0
            )

            gender_statistics.append({
                'gender': gender,
                'total': total,
                'with_marks': with_marks,
                'average': round(avg, 2)
            })

        # ==================================================
        # 8. SUBJECT PERFORMANCE (THIS SUBJECT)
        # ==================================================
        subject_performance = results.aggregate(
            average=Avg('marks_obtained'),
            highest=Max('marks_obtained'),
            lowest=Min('marks_obtained')
        )

        # ==================================================
        # 9. SUBJECT POSITION IN EXAM SESSION
        # ==================================================
        subject_averages = (
            StudentResult.objects
            .filter(exam_session=exam_session)
            .values('subject')
            .annotate(avg_marks=Avg('marks_obtained'))
            .order_by('-avg_marks')
        )

        subject_position = None
        total_subjects = len(subject_averages)

        for index, row in enumerate(subject_averages, start=1):
            if row['subject'] == subject.id:
                subject_position = index
                break

        subject_ranking = {
            'position': subject_position,
            'total_subjects': total_subjects
        }

        # ==================================================
        # 10. CONTEXT
        # ==================================================
        context = {
            'exam_session': exam_session,
            'subject': subject,
            'students_data': students_data,
            'statistics': statistics,
            'grade_distribution': grade_distribution,
            'gender_statistics': gender_statistics,
            'subject_performance': subject_performance,
            'subject_ranking': subject_ranking,
            'today': timezone.now().date(),
            'generated_by': request.user.get_full_name() or request.user.username,
        }

        # ==================================================
        # 11. RENDER PDF
        # ==================================================
        html_string = render_to_string(
            'admin/results/pdf_subject_report.html',
            context
        )

        pdf = HTML(
            string=html_string,
            base_url=request.build_absolute_uri()
        ).write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename='
            f'"Marks_Report_{subject.code}_{exam_session.name}.pdf"'
        )

        return response

    except Exception as e:
        messages.error(request, f"Error generating PDF: {e}")
        return redirect('manage_results', exam_session_id=exam_session_id)


# Add these new views to the existing file

@login_required
def download_session_excel_template(request, exam_session_id):
    """Generate and download Excel template for entire exam session"""
    try:
        exam_session = get_object_or_404(
            ExamSession.objects.select_related(
                'exam_type', 'class_level', 'stream_class',
                'academic_year', 'term'
            ),
            id=exam_session_id
        )
        
        subjects = Subject.objects.filter(
            educational_level=exam_session.class_level.educational_level,
            is_active=True
        ).order_by('code')
        
        # Get students for this exam session
        if exam_session.stream_class:
            students = Student.objects.filter(
                class_level=exam_session.class_level,
                stream_class=exam_session.stream_class,
                is_active=True
            )
        else:
            students = Student.objects.filter(
                class_level=exam_session.class_level,
                is_active=True
            )
        
        students = students.order_by('first_name', 'last_name')
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Session Marks Entry"
        
        # Define styles
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        header_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        info_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        info_font = Font(name="Arial", size=10, bold=True)
        
        cell_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        
        # Add header information
        ws['A1'] = "EXAM SESSION MARKS ENTRY TEMPLATE"
        ws['A1'].font = Font(name="Arial", size=14, bold=True)
        ws['A1'].alignment = center_alignment
        ws.merge_cells(f'A1:{get_column_letter(3 + len(subjects))}1')
        
        ws['A2'] = f"Exam Session: {exam_session.name}"
        ws['A2'].font = info_font
        ws.merge_cells(f'A2:{get_column_letter(3 + len(subjects))}2')
        
        ws['A3'] = f"Class: {exam_session.class_level.name}"
        if exam_session.stream_class:
            ws['A3'] += f" {exam_session.stream_class.stream_letter}"
        ws['A3'].font = info_font
        ws.merge_cells(f'A3:{get_column_letter(3 + len(subjects))}3')
        
        ws['A4'] = f"Academic Year: {exam_session.academic_year.name} - Term: {exam_session.term.get_term_number_display()}"
        ws['A4'].font = info_font
        ws.merge_cells(f'A4:{get_column_letter(3 + len(subjects))}4')
        
        ws['A5'] = f"Maximum Score per Subject: {exam_session.exam_type.max_score}"
        ws['A5'].font = info_font
        ws.merge_cells(f'A5:{get_column_letter(3 + len(subjects))}5')
        
        # Add instruction rows
        ws['A7'] = "INSTRUCTIONS:"
        ws['A7'].font = Font(name="Arial", size=11, bold=True, color="FF0000")
        ws.merge_cells(f'A7:{get_column_letter(3 + len(subjects))}7')
        
        instructions = [
            "1. Fill marks in the subject columns (Column D onwards).",
            "2. Leave cells blank for absent students or unmarked subjects.",
            "3. Enter 0 for zero marks (it's a valid mark).",
            "4. Do not modify Student ID, Registration No., or Student Name columns.",
            f"5. Marks range: 0 - {exam_session.exam_type.max_score} for each subject",
            "6. Save file and upload using the upload feature.",
            "7. All subjects are included in this template."
        ]
        
        for i, instruction in enumerate(instructions, start=8):
            cell = ws[f'A{i}']
            cell.value = instruction
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(wrap_text=True)
            ws.merge_cells(f'A{i}:{get_column_letter(3 + len(subjects))}{i}')
        
        # Add headers for data
        header_row = 15
        headers = ["Student ID", "Registration No.", "Student Name"]
        
        # Add subject headers
        for subject in subjects:
            headers.append(f"{subject.name}")
        
        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            # Set column widths
            if col_num <= 3:
                ws.column_dimensions[get_column_letter(col_num)].width = 20
            else:
                ws.column_dimensions[get_column_letter(col_num)].width = 15
        
        # Add student data
        data_start_row = header_row + 1
        
        for i, student in enumerate(students, start=data_start_row):
            # Student ID
            ws.cell(row=i, column=1, value=student.id)
            ws.cell(row=i, column=1).border = cell_border
            ws.cell(row=i, column=1).alignment = center_alignment
            
            # Registration Number
            ws.cell(row=i, column=2, value=student.registration_number or f"S{student.id:04d}")
            ws.cell(row=i, column=2).border = cell_border
            ws.cell(row=i, column=2).alignment = left_alignment
            
            # Student Name
            ws.cell(row=i, column=3, value=student.full_name)
            ws.cell(row=i, column=3).border = cell_border
            ws.cell(row=i, column=3).alignment = left_alignment
            
            # Get existing results for this student
            existing_results = StudentResult.objects.filter(
                exam_session=exam_session,
                student=student
            ).select_related('subject')
            
            results_dict = {r.subject_id: r.marks_obtained for r in existing_results}
            
            # Add marks columns for each subject
            for col_num, subject in enumerate(subjects, start=4):
                existing_marks = results_dict.get(subject.id)
                cell = ws.cell(row=i, column=col_num, value=existing_marks)
                cell.border = cell_border
                cell.alignment = center_alignment
                
                # Add data validation for marks
                if exam_session.exam_type.max_score:
                    dv = openpyxl.worksheet.datavalidation.DataValidation(
                        type="decimal",
                        operator="between",
                        formula1=0,
                        formula2=exam_session.exam_type.max_score,
                        allow_blank=True,
                        showErrorMessage=True,
                        errorTitle="Invalid Marks",
                        error=f"Marks must be between 0 and {exam_session.exam_type.max_score}"
                    )
                    ws.add_data_validation(dv)
                    dv.add(f'{get_column_letter(col_num)}{i}:{get_column_letter(col_num)}{i}')
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Session_Template_{exam_session.name.replace(' ', '_')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Save workbook to response
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating template: {str(e)}", status=500)

@login_required
@require_POST
def upload_session_excel(request):
    excel_file = request.FILES.get('excel_file')
    exam_session_id = request.POST.get('exam_session_id')

    if not excel_file or not exam_session_id:
        return JsonResponse({'success': False, 'message': 'Missing file or exam session ID'})

    exam_session = get_object_or_404(ExamSession, id=exam_session_id)

    if exam_session.status == 'published':
        return JsonResponse({'success': False, 'message': 'Cannot modify a published exam session'})

    wb = openpyxl.load_workbook(excel_file, data_only=True)
    ws = wb.active

    subjects = Subject.objects.filter(
        educational_level=exam_session.class_level.educational_level,
        is_active=True
    )

    subject_map = {
        normalize(subject.name): subject
        for subject in subjects
    }

    # ----------------------------
    # FIND HEADER ROW
    # ----------------------------
    header_row_idx = None
    header_values = []

    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
        if row and "Student ID" in [str(c) for c in row if c]:
            header_row_idx = i
            header_values = [normalize(str(c)) for c in row]
            break

    if not header_row_idx:
        return JsonResponse({'success': False, 'message': 'Header row not found'})

    # ----------------------------
    # MAP SUBJECT COLUMNS
    # ----------------------------
    subject_columns = {}

    for idx, header in enumerate(header_values):
        if header in subject_map:
            subject_columns[idx] = subject_map[header]

    if not subject_columns:
        return JsonResponse({'success': False, 'message': 'No valid subject columns found'})

    processed = 0
    errors = []

    with transaction.atomic():
        for row_idx, row in enumerate(
            ws.iter_rows(min_row=header_row_idx + 1, values_only=True),
            start=header_row_idx + 1
        ):
            if not row or not row[0]:
                continue

            try:
                student = Student.objects.get(id=int(row[0]), is_active=True)
            except Student.DoesNotExist:
                errors.append(f"Row {row_idx}: Invalid student ID")
                continue

            for col_idx, subject in subject_columns.items():
                if col_idx >= len(row):
                    continue

                marks = row[col_idx]

                if marks is None or marks == "":
                    continue

                try:
                    marks = Decimal(str(marks))
                except:
                    errors.append(f"Row {row_idx}, {subject.name}: Invalid mark")
                    continue

                max_score = exam_session.exam_type.max_score
                if marks < 0 or marks > max_score:
                    errors.append(f"Row {row_idx}, {subject.name}: Out of range")
                    continue

                result, _ = StudentResult.objects.get_or_create(
                    exam_session=exam_session,
                    student=student,
                    subject=subject
                )

                result.marks_obtained = marks
                result.percentage = (marks / Decimal(max_score)) * 100

                grade_scale = GradingScale.objects.filter(
                    education_level=exam_session.class_level.educational_level,
                    min_mark__lte=marks,
                    max_mark__gte=marks
                ).first()

                if grade_scale:
                    result.grade = grade_scale.grade
                    result.grade_point = grade_scale.points

                result.save()
                processed += 1

    return JsonResponse({
        'success': True,
        'message': f'Processed {processed} marks successfully',
        'errors': errors[:10]
    })

def normalize(text):
    return text.strip().lower() if text else ""


@login_required
def download_session_excel_report(request, exam_session_id):
    """Generate comprehensive Excel report for entire exam session with subject-wise performance"""
    try:
        exam_session = get_object_or_404(
            ExamSession.objects.select_related(
                'exam_type',
                'class_level',
                'stream_class',
                'academic_year',
                'term',
                'class_level__educational_level'
            ),
            id=exam_session_id
        )

        subjects = list(
            Subject.objects.filter(
                educational_level=exam_session.class_level.educational_level,
                is_active=True
            ).order_by('code')
        )

        # Get students
        student_qs = Student.objects.filter(
            class_level=exam_session.class_level,
            is_active=True
        )
        if exam_session.stream_class:
            student_qs = student_qs.filter(stream_class=exam_session.stream_class)
        
        students = list(student_qs.order_by('first_name', 'last_name'))

        # Get all results
        results = StudentResult.objects.filter(
            exam_session=exam_session
        ).select_related('student', 'subject')

        # Get metrics and positions
        metrics = StudentExamMetrics.objects.filter(
            exam_session=exam_session
        ).select_related('student', 'division')

        positions = StudentExamPosition.objects.filter(
            exam_session=exam_session
        ).select_related('student')

        # Create lookup dictionaries
        results_map = {}
        for r in results:
            results_map.setdefault(r.student_id, {})[r.subject_id] = r

        metrics_map = {m.student_id: m for m in metrics}
        position_map = {p.student_id: p for p in positions}

        # ============================================
        # CREATE EXCEL WORKBOOK
        # ============================================
        wb = openpyxl.Workbook()
        
        # ============================================
        # SHEET 1: COMPREHENSIVE RESULTS
        # ============================================
        ws_main = wb.active
        ws_main.title = "Comprehensive Results"
        
        # Define styles
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Arial", size=14, bold=True)
        info_font = Font(name="Arial", size=10, bold=True)
        normal_font = Font(name="Arial", size=10)
        bold_font = Font(name="Arial", size=10, bold=True)
        
        header_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        cell_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        center_alignment = Alignment(horizontal="center", vertical="center")
        left_alignment = Alignment(horizontal="left", vertical="center")
        
        # Add header information
        ws_main['A1'] = "EXAM SESSION COMPREHENSIVE REPORT"
        ws_main['A1'].font = title_font
        ws_main['A1'].alignment = center_alignment
        ws_main.merge_cells(f'A1:{get_column_letter(7 + len(subjects))}1')
        
        ws_main['A2'] = f"Exam Session: {exam_session.name}"
        ws_main['A2'].font = info_font
        ws_main.merge_cells(f'A2:{get_column_letter(7 + len(subjects))}2')
        
        ws_main['A3'] = f"Class: {exam_session.class_level.name}"
        if exam_session.stream_class:
            ws_main['A3'] += f" {exam_session.stream_class.stream_letter}"
        ws_main['A3'].font = info_font
        ws_main.merge_cells(f'A3:{get_column_letter(7 + len(subjects))}3')
        
        ws_main['A4'] = f"Academic Year: {exam_session.academic_year.name} | Term: {exam_session.term.get_term_number_display()}"
        ws_main['A4'].font = info_font
        ws_main.merge_cells(f'A4:{get_column_letter(7 + len(subjects))}4')
        
        ws_main['A5'] = f"Exam Date: {exam_session.exam_date.strftime('%B %d, %Y')}"
        ws_main['A5'].font = info_font
        ws_main.merge_cells(f'A5:{get_column_letter(7 + len(subjects))}5')
        
        # Column headers
        header_row = 7
        headers = ["S.No", "Registration No.", "Student Name", "Gender"]
        
        # Add subject headers
        for subject in subjects:
            headers.append(f"{subject.name}")
        
        headers.extend(["Total Marks", "Average", "Grade Points", "Division", "Position"])
        
        # Write headers
        for col_num, header in enumerate(headers, start=1):
            cell = ws_main.cell(row=header_row, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            
            # Set column widths
            if col_num == 1:  # S.No
                ws_main.column_dimensions[get_column_letter(col_num)].width = 8
            elif col_num == 2:  # Reg No
                ws_main.column_dimensions[get_column_letter(col_num)].width = 15
            elif col_num == 3:  # Name
                ws_main.column_dimensions[get_column_letter(col_num)].width = 25
            elif col_num == 4:  # Gender
                ws_main.column_dimensions[get_column_letter(col_num)].width = 10
            elif col_num <= 4 + len(subjects):  # Subject columns
                ws_main.column_dimensions[get_column_letter(col_num)].width = 12
            else:  # Summary columns
                ws_main.column_dimensions[get_column_letter(col_num)].width = 15
        
        # Add student data
        data_start_row = header_row + 1
        
        for i, student in enumerate(students, start=data_start_row):
            # Basic info
            ws_main.cell(row=i, column=1, value=i - header_row).border = cell_border
            ws_main.cell(row=i, column=2, value=student.registration_number or f"S{student.id:04d}").border = cell_border
            ws_main.cell(row=i, column=3, value=student.full_name).border = cell_border
            ws_main.cell(row=i, column=4, value=student.get_gender_display()).border = cell_border
            
            # Subject marks
            total_marks = 0
            subjects_with_marks = 0
            
            for col_num, subject in enumerate(subjects, start=5):
                result = results_map.get(student.id, {}).get(subject.id)
                if result and result.marks_obtained is not None:
                    marks = result.marks_obtained
                    grade = result.grade or ""
                    cell_value = f"{marks:.1f}"
                    if grade:
                        cell_value += f" ({grade})"
                    
                    ws_main.cell(row=i, column=col_num, value=cell_value)
                    
                    total_marks += float(marks)
                    subjects_with_marks += 1
                else:
                    ws_main.cell(row=i, column=col_num, value="-")
                
                ws_main.cell(row=i, column=col_num).border = cell_border
                ws_main.cell(row=i, column=col_num).alignment = center_alignment
            
            # Summary columns
            summary_col = 5 + len(subjects)
            
            # Total Marks
            ws_main.cell(row=i, column=summary_col, value=total_marks if subjects_with_marks > 0 else "-")
            ws_main.cell(row=i, column=summary_col).border = cell_border
            ws_main.cell(row=i, column=summary_col).alignment = center_alignment
            
            # Average
            average = total_marks / subjects_with_marks if subjects_with_marks > 0 else None
            ws_main.cell(row=i, column=summary_col + 1, value=f"{average:.2f}" if average else "-")
            ws_main.cell(row=i, column=summary_col + 1).border = cell_border
            ws_main.cell(row=i, column=summary_col + 1).alignment = center_alignment
            
            # Grade Points (from metrics)
            metrics = metrics_map.get(student.id)
            ws_main.cell(row=i, column=summary_col + 2, 
                        value=f"{metrics.total_grade_points:.1f}" if metrics and metrics.total_grade_points else "-")
            ws_main.cell(row=i, column=summary_col + 2).border = cell_border
            ws_main.cell(row=i, column=summary_col + 2).alignment = center_alignment
            
            # Division
            division = metrics.division.division if metrics and metrics.division else "-"
            ws_main.cell(row=i, column=summary_col + 3, value=division)
            ws_main.cell(row=i, column=summary_col + 3).border = cell_border
            ws_main.cell(row=i, column=summary_col + 3).alignment = center_alignment
            
            # Position
            position = position_map.get(student.id)
            ws_main.cell(row=i, column=summary_col + 4, 
                        value=position.class_position if position and position.class_position else "-")
            ws_main.cell(row=i, column=summary_col + 4).border = cell_border
            ws_main.cell(row=i, column=summary_col + 4).alignment = center_alignment
        
        # Add summary statistics at the bottom
        summary_start = data_start_row + len(students) + 2
        
        ws_main.cell(row=summary_start, column=1, value="SUMMARY STATISTICS").font = title_font
        ws_main.merge_cells(f'A{summary_start}:C{summary_start}')
        
        summary_rows = [
            ("Total Students", len(students)),
            ("Total Subjects", len(subjects)),
            ("Exam Type", exam_session.exam_type.name),
            ("Max Score per Subject", f"{exam_session.exam_type.max_score:.1f}"),
            ("Report Generated", timezone.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Generated By", request.user.get_full_name() or request.user.username),
        ]
        
        for idx, (label, value) in enumerate(summary_rows, start=1):
            ws_main.cell(row=summary_start + idx, column=1, value=label).font = bold_font
            ws_main.cell(row=summary_start + idx, column=2, value=value).font = normal_font
        
        # ============================================
        # SHEET 2: SUBJECT-WISE PERFORMANCE
        # ============================================
        ws_performance = wb.create_sheet(title="Subject Performance")
        
        # Title
        ws_performance['A1'] = "SUBJECT-WISE PERFORMANCE ANALYSIS"
        ws_performance['A1'].font = title_font
        ws_performance.merge_cells('A1:G1')
        ws_performance['A1'].alignment = center_alignment
        
        # Headers for subject performance
        perf_headers = ["Subject Code", "Subject Name", "Students with Marks", 
                        "Average Marks", "Highest Marks", "Lowest Marks", 
                        "Pass Rate (%)", "Grade Distribution"]
        
        for col_num, header in enumerate(perf_headers, start=1):
            cell = ws_performance.cell(row=3, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            
            # Set column widths
            if col_num == 1:  # Code
                ws_performance.column_dimensions[get_column_letter(col_num)].width = 12
            elif col_num == 2:  # Name
                ws_performance.column_dimensions[get_column_letter(col_num)].width = 30
            elif col_num in [3, 7]:  # Count and Pass Rate
                ws_performance.column_dimensions[get_column_letter(col_num)].width = 18
            elif col_num == 8:  # Grade Distribution
                ws_performance.column_dimensions[get_column_letter(col_num)].width = 25
            else:  # Marks columns
                ws_performance.column_dimensions[get_column_letter(col_num)].width = 15
        
        # Calculate subject performance
        perf_start_row = 4
        
        for idx, subject in enumerate(subjects, start=perf_start_row):
            subject_results = results.filter(subject=subject, marks_obtained__isnull=False)
            marks_list = [float(r.marks_obtained) for r in subject_results if r.marks_obtained is not None]
            
            # Basic info
            ws_performance.cell(row=idx, column=1, value=subject.code).border = cell_border
            ws_performance.cell(row=idx, column=2, value=subject.name).border = cell_border
            
            # Students with marks
            students_with_marks = len(marks_list)
            ws_performance.cell(row=idx, column=3, value=students_with_marks).border = cell_border
            ws_performance.cell(row=idx, column=3).alignment = center_alignment
            
            if marks_list:
                # Average marks
                avg_marks = sum(marks_list) / len(marks_list)
                ws_performance.cell(row=idx, column=4, value=f"{avg_marks:.2f}").border = cell_border
                ws_performance.cell(row=idx, column=4).alignment = center_alignment
                
                # Highest marks
                highest = max(marks_list)
                ws_performance.cell(row=idx, column=5, value=f"{highest:.1f}").border = cell_border
                ws_performance.cell(row=idx, column=5).alignment = center_alignment
                
                # Lowest marks
                lowest = min(marks_list)
                ws_performance.cell(row=idx, column=6, value=f"{lowest:.1f}").border = cell_border
                ws_performance.cell(row=idx, column=6).alignment = center_alignment
                
                # Pass rate (assuming pass mark is 40)
                pass_mark = 40
                passed = sum(1 for m in marks_list if m >= pass_mark)
                pass_rate = (passed / len(marks_list)) * 100 if marks_list else 0
                ws_performance.cell(row=idx, column=7, value=f"{pass_rate:.1f}%").border = cell_border
                ws_performance.cell(row=idx, column=7).alignment = center_alignment
                
                # Grade distribution
                grades = {}
                for r in subject_results:
                    if r.grade:
                        grades[r.grade] = grades.get(r.grade, 0) + 1
                
                grade_dist = ", ".join([f"{grade}:{count}" for grade, count in grades.items()])
                ws_performance.cell(row=idx, column=8, value=grade_dist).border = cell_border
            else:
                # No marks for this subject
                for col in range(4, 9):
                    ws_performance.cell(row=idx, column=col, value="-").border = cell_border
                    ws_performance.cell(row=idx, column=col).alignment = center_alignment
        
        # Add subject performance summary
        perf_summary_row = perf_start_row + len(subjects) + 2
        ws_performance.cell(row=perf_summary_row, column=1, value="PERFORMANCE SUMMARY").font = title_font
        ws_performance.merge_cells(f'A{perf_summary_row}:B{perf_summary_row}')
        
        # ============================================
        # SHEET 3: GRADE DISTRIBUTION
        # ============================================
        ws_grades = wb.create_sheet(title="Grade Distribution")
        
        # Title
        ws_grades['A1'] = "GRADE DISTRIBUTION ACROSS ALL SUBJECTS"
        ws_grades['A1'].font = title_font
        ws_grades.merge_cells('A1:D1')
        ws_grades['A1'].alignment = center_alignment
        
        # Grade headers
        grade_headers = ["Grade", "Description", "Marks Range", "Count", "Percentage (%)"]
        
        for col_num, header in enumerate(grade_headers, start=1):
            cell = ws_grades.cell(row=3, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            
            # Set column widths
            if col_num == 2:  # Description
                ws_grades.column_dimensions[get_column_letter(col_num)].width = 20
            else:
                ws_grades.column_dimensions[get_column_letter(col_num)].width = 15
        
        # Grade definitions and counts
        grade_definitions = [
            ("A", "Excellent", "80-100"),
            ("B", "Very Good", "70-79"),
            ("C", "Good", "60-69"),
            ("D", "Satisfactory", "50-59"),
            ("E", "Fair", "40-49"),
            ("F", "Fail", "0-39"),
            ("S", "Subsidiary", "N/A"),
        ]
        
        # Count grades across all results
        grade_counts = {}
        total_grades = 0
        
        for result in results:
            if result.grade:
                grade_counts[result.grade] = grade_counts.get(result.grade, 0) + 1
                total_grades += 1
        
        # Write grade data
        grade_start_row = 4
        
        for idx, (grade, description, range_text) in enumerate(grade_definitions, start=grade_start_row):
            ws_grades.cell(row=idx, column=1, value=grade).border = cell_border
            ws_grades.cell(row=idx, column=2, value=description).border = cell_border
            ws_grades.cell(row=idx, column=3, value=range_text).border = cell_border
            
            count = grade_counts.get(grade, 0)
            ws_grades.cell(row=idx, column=4, value=count).border = cell_border
            ws_grades.cell(row=idx, column=4).alignment = center_alignment
            
            percentage = (count / total_grades * 100) if total_grades > 0 else 0
            ws_grades.cell(row=idx, column=5, value=f"{percentage:.1f}%").border = cell_border
            ws_grades.cell(row=idx, column=5).alignment = center_alignment
        
        # Add total row
        total_row = grade_start_row + len(grade_definitions)
        ws_grades.cell(row=total_row, column=3, value="TOTAL").font = bold_font
        ws_grades.cell(row=total_row, column=3).border = cell_border
        
        ws_grades.cell(row=total_row, column=4, value=total_grades).font = bold_font
        ws_grades.cell(row=total_row, column=4).border = cell_border
        ws_grades.cell(row=total_row, column=4).alignment = center_alignment
        
        ws_grades.cell(row=total_row, column=5, value="100.0%").font = bold_font
        ws_grades.cell(row=total_row, column=5).border = cell_border
        ws_grades.cell(row=total_row, column=5).alignment = center_alignment
        
        # ============================================
        # SHEET 4: TOP PERFORMERS
        # ============================================
        ws_top = wb.create_sheet(title="Top Performers")
        
        # Title
        ws_top['A1'] = "TOP PERFORMERS - CLASS RANKING"
        ws_top['A1'].font = title_font
        ws_top.merge_cells('A1:F1')
        ws_top['A1'].alignment = center_alignment
        
        # Headers
        top_headers = ["Position", "Registration No.", "Student Name", 
                      "Total Marks", "Average", "Division"]
        
        for col_num, header in enumerate(top_headers, start=1):
            cell = ws_top.cell(row=3, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = header_border
            cell.alignment = center_alignment
            
            # Set column widths
            if col_num == 3:  # Name
                ws_top.column_dimensions[get_column_letter(col_num)].width = 25
            else:
                ws_top.column_dimensions[get_column_letter(col_num)].width = 15
        
        # Get top 10 performers based on position
        top_students = []
        for position in positions.order_by('class_position')[:20]:  # Top 20
            metrics = metrics_map.get(position.student_id)
            if metrics and position.class_position:
                student = next((s for s in students if s.id == position.student_id), None)
                if student:
                    top_students.append({
                        'position': position.class_position,
                        'reg_no': student.registration_number or f"S{student.id:04d}",
                        'name': student.full_name,
                        'total_marks': metrics.total_marks,
                        'average': metrics.average_marks,
                        'division': metrics.division.division if metrics.division else "-"
                    })
        
        # Write top performers
        top_start_row = 4
        
        for idx, student_data in enumerate(top_students, start=top_start_row):
            ws_top.cell(row=idx, column=1, value=student_data['position']).border = cell_border
            ws_top.cell(row=idx, column=1).alignment = center_alignment
            
            ws_top.cell(row=idx, column=2, value=student_data['reg_no']).border = cell_border
            
            ws_top.cell(row=idx, column=3, value=student_data['name']).border = cell_border
            
            ws_top.cell(row=idx, column=4, 
                       value=f"{student_data['total_marks']:.1f}" if student_data['total_marks'] else "-").border = cell_border
            ws_top.cell(row=idx, column=4).alignment = center_alignment
            
            ws_top.cell(row=idx, column=5, 
                       value=f"{student_data['average']:.2f}" if student_data['average'] else "-").border = cell_border
            ws_top.cell(row=idx, column=5).alignment = center_alignment
            
            ws_top.cell(row=idx, column=6, value=student_data['division']).border = cell_border
            ws_top.cell(row=idx, column=6).alignment = center_alignment
        
        # ============================================
        # CREATE RESPONSE
        # ============================================
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"Session_Report_{exam_session.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Save workbook to response
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating Excel report: {str(e)}", status=500)
    

@login_required
def download_session_summary(request, exam_session_id):
    """Download session summary as CSV"""
    try:
        exam_session = get_object_or_404(ExamSession, id=exam_session_id)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Session_Summary_{exam_session.name}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow(['Exam Session Summary', exam_session.name])
        writer.writerow(['Academic Year', exam_session.academic_year.name])
        writer.writerow(['Term', exam_session.term.get_term_number_display()])
        writer.writerow(['Class', exam_session.class_level.name])
        writer.writerow(['Stream', exam_session.stream_class.stream_letter if exam_session.stream_class else 'All'])
        writer.writerow(['Exam Date', exam_session.exam_date])
        writer.writerow([])
        
        # Add summary statistics
        writer.writerow(['Summary Statistics'])
        # You can add more statistics here
        
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating summary: {str(e)}", status=500)