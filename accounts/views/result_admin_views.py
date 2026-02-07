# results/views/grading_scales.py
from datetime import date, datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
import json
from results.models import  ExamSession, ExamType, GradingScale, DivisionScale, StudentExamMetrics, StudentExamPosition, StudentResult
from core.models import AcademicYear, ClassLevel, EducationalLevel, StreamClass, Subject, Term
from django.contrib import messages
from students.models import Student
from django.db.models import Count, Sum, Avg, Max, Min
from django.utils import timezone
from django.utils.timesince import timesince
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
import pandas as pd
from io import BytesIO
import openpyxl
from openpyxl.utils import get_column_letter
import csv
import math

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
        min_mark_val = float(min_mark)
        max_mark_val = float(max_mark)
        points_val = float(points) if points else 0.0
    except ValueError:
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
        min_mark_val = float(min_mark)
        max_mark_val = float(max_mark)
        points_val = float(points) if points else grading_scale.points
    except ValueError:
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
        if not exam_session.papers.exists():
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
    if exam_session.papers.exists():
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
    """Save multiple student results"""
    try:
        data = json.loads(request.body)
        exam_session_id = data.get('exam_session_id')
        results_data = data.get('results', [])
        is_auto_save = data.get('is_auto_save', False)
        
        if not exam_session_id or not results_data:
            return JsonResponse({
                'success': False,
                'message': 'Invalid data provided.'
            })
        
        exam_session = get_object_or_404(ExamSession, id=exam_session_id)
        
        saved_results = []
        saved_count = 0
        
        with transaction.atomic():
            for result_data in results_data:
                student_id = result_data.get('student_id')
                subject_id = result_data.get('subject_id')
                marks_obtained = result_data.get('marks_obtained')
                
                if not all([student_id, subject_id, marks_obtained is not None]):
                    continue
                
                try:
                    # Get or create result
                    result, created = StudentResult.objects.get_or_create(
                        exam_session=exam_session,
                        student_id=student_id,
                        subject_id=subject_id,
                        defaults={'marks_obtained': marks_obtained}
                    )
                    
                    if not created:
                        result.marks_obtained = marks_obtained
                    
                    # Calculate percentage
                    max_score = exam_session.exam_type.max_score
                    if max_score > 0:
                        result.percentage = (marks_obtained / max_score) * 100
                    
                    # Calculate grade
                    education_level = exam_session.class_level.educational_level
                    grade_scale = GradingScale.objects.filter(
                        education_level=education_level,
                        min_mark__lte=marks_obtained,
                        max_mark__gte=marks_obtained
                    ).first()
                    
                    if grade_scale:
                        result.grade = grade_scale.grade
                        result.grade_point = grade_scale.points
                    
                    result.save()
                    
                    saved_results.append({
                        'student_id': student_id,
                        'subject_id': subject_id,
                        'result_id': result.id
                    })
                    saved_count += 1
                    
                except (Student.DoesNotExist, Subject.DoesNotExist):
                    continue
                except ValidationError as e:
                    continue
        
        # Calculate positions after saving results
        if saved_count > 0 and not is_auto_save:
            calculate_subject_positions(exam_session)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully saved {saved_count} results.',
            'saved_count': saved_count,
            'saved_results': saved_results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving results: {str(e)}'
        })

@login_required
@require_POST
def save_multiple_results(request):
    """Save multiple new results from modal"""
    try:
        exam_session_id = request.POST.get('exam_session_id')
        results_json = request.POST.get('results')
        
        if not exam_session_id or not results_json:
            return JsonResponse({
                'success': False,
                'message': 'Invalid data provided.'
            })
        
        results_data = json.loads(results_json)
        exam_session = get_object_or_404(ExamSession, id=exam_session_id)
        
        saved_count = 0
        errors = []
        
        with transaction.atomic():
            for result_data in results_data:
                try:
                    # Check if result already exists
                    existing_result = StudentResult.objects.filter(
                        exam_session=exam_session,
                        student_id=result_data['studentId'],
                        subject_id=result_data['subjectId']
                    ).exists()
                    
                    if existing_result:
                        errors.append(f"Result already exists for student {result_data['studentId']} and subject {result_data['subjectId']}")
                        continue
                    
                    # Create new result
                    result = StudentResult.objects.create(
                        exam_session=exam_session,
                        student_id=result_data['studentId'],
                        subject_id=result_data['subjectId'],
                        marks_obtained=result_data['marks']
                    )
                    
                    # Calculate percentage
                    max_score = exam_session.exam_type.max_score
                    if max_score > 0:
                        result.percentage = (result.marks_obtained / max_score) * 100
                    
                    # Calculate grade
                    education_level = exam_session.class_level.educational_level
                    grade_scale = GradingScale.objects.filter(
                        education_level=education_level,
                        min_mark__lte=result.marks_obtained,
                        max_mark__gte=result.marks_obtained
                    ).first()
                    
                    if grade_scale:
                        result.grade = grade_scale.grade
                        result.grade_point = grade_scale.points
                    
                    result.save()
                    saved_count += 1
                    
                except Exception as e:
                    errors.append(str(e))
                    continue
        
        # Calculate positions
        if saved_count > 0:
            calculate_subject_positions(exam_session)
        
        response_data = {
            'success': True,
            'message': f'Successfully saved {saved_count} results.',
            'saved_count': saved_count
        }
        
        if errors:
            response_data['errors'] = errors[:5]  # Limit errors to first 5
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving results: {str(e)}'
        })


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