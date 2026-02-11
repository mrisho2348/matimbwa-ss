from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum, Avg, Count, F, Q
from decimal import Decimal, InvalidOperation
import logging

from core.models import CombinationSubject
from .models import (
    ExamSession, StudentResult, StudentExamMetrics, StudentExamPosition,
    GradingScale, DivisionScale, Subject
)
from students.models import Student

logger = logging.getLogger(__name__)


# Flag to prevent infinite recursion
_UPDATING_METRICS = False


@receiver([post_save, post_delete], sender=StudentResult)
def update_student_metrics(sender, instance, **kwargs):
    """
    Signal to update student metrics and positions when results change.
    Handles both individual and bulk operations.
    """
    global _UPDATING_METRICS
    
    # Prevent infinite recursion
    if _UPDATING_METRICS:
        return
    
    try:
        _UPDATING_METRICS = True
        
        with transaction.atomic():
            exam_session = instance.exam_session
            student = instance.student
            education_level = exam_session.class_level.educational_level
            
            # Calculate metrics for this student
            should_calculate_metrics = calculate_student_metrics(exam_session, student, education_level)
            
            # Recalculate positions for the entire exam session
            if should_calculate_metrics:
                calculate_all_positions(exam_session)
            
    except Exception as e:
        logger.error(f"Error updating student metrics: {str(e)}", exc_info=True)
    finally:
        _UPDATING_METRICS = False


def calculate_student_metrics(exam_session, student, education_level):
    """
    Calculate comprehensive metrics for a student in an exam session.
    Returns True if metrics were calculated, False if not.
    
    O-Level Rules:
    1. Must have at least 7 subjects with valid grade points
    2. Take best 7 grade points for calculation
    3. If less than 7 subjects, no metrics/positions should be calculated
    """
    global _UPDATING_METRICS
    
    # Prevent infinite recursion
    if _UPDATING_METRICS:
        return False
    
    try:
        _UPDATING_METRICS = True
        
        # Get all results for this student in this exam session
        results = StudentResult.objects.filter(
            exam_session=exam_session,
            student=student,
            marks_obtained__isnull=False
        ).select_related('subject')
        
        # Check if we have any results
        if not results.exists():
            # Delete metrics if no results
            StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student=student
            ).delete()
            return False
        
        # EDUCATION LEVEL SPECIFIC VALIDATION
        level_code = education_level.code.upper() if education_level.code else ''
        
        if level_code == 'O_LEVEL':
            # For O-Level, validate we have at least 7 subjects with grade points
            subjects_with_grade_points = []
            for result in results:
                if result.grade_point is not None:
                    try:
                        gp = Decimal(str(result.grade_point))
                        subjects_with_grade_points.append((result.subject_id, gp))
                    except (InvalidOperation, TypeError):
                        continue
            
            if len(subjects_with_grade_points) < 7:
                # Not enough subjects with grade points - delete metrics
                StudentExamMetrics.objects.filter(
                    exam_session=exam_session,
                    student=student
                ).delete()
                return False
                
            # Sort subjects by grade points (descending) and take best 7
            subjects_with_grade_points.sort(key=lambda x: x[1], reverse=True)
            best_7_points = subjects_with_grade_points[:7]
            
            # Calculate total grade points from best 7
            total_grade_points = sum(gp for _, gp in best_7_points)
            
            # Determine division based on total grade points
            division = None
            try:
                points_int = int(total_grade_points)
                division = DivisionScale.objects.filter(
                    education_level=education_level,
                    min_points__lte=points_int,
                    max_points__gte=points_int
                ).first()
            except (ValueError, TypeError) as e:
                logger.error(f"Error determining division for student {student.id}: {str(e)}")
                division = None
            
            # Now calculate basic statistics from ALL subjects (not just best 7)
            marks_list = [float(r.marks_obtained) for r in results if r.marks_obtained is not None]
            marks_sum = sum(marks_list)
            total_marks = Decimal(str(marks_sum))
            
            subject_count = len(marks_list)
            average_marks = Decimal(str(marks_sum / subject_count)) if subject_count > 0 else Decimal('0.0')
            
            # Calculate percentage based on exam type max score
            max_score = float(exam_session.exam_type.max_score)
            average_percentage = Decimal(str((float(average_marks) / max_score * 100))) if max_score > 0 else Decimal('0.0')
            
            # Calculate average grade and remark
            average_grade = calculate_average_grade(float(average_percentage))
            average_remark = calculate_remark(float(average_percentage))
            
            # Prepare metrics data
            metrics_data = {
                'total_marks': total_marks,
                'average_marks': average_marks,
                'average_percentage': average_percentage,
                'average_grade': average_grade,
                'average_remark': average_remark,
                'total_grade_points': total_grade_points,
                'division': division,
            }
            
            # Update or create metrics
            StudentExamMetrics.objects.update_or_create(
                exam_session=exam_session,
                student=student,
                defaults=metrics_data
            )
            
            return True
            
        elif level_code == 'A_LEVEL':
            # A-Level calculation remains the same
            return handle_a_level_calculation(exam_session, student, education_level, results)
            
        else:
            # Primary/Nursery - no grade points or division
            return handle_primary_calculation(exam_session, student, results)
            
    except Exception as e:
        logger.error(f"Error calculating metrics for student {student.id}: {str(e)}", exc_info=True)
        return False
    finally:
        _UPDATING_METRICS = False


def handle_a_level_calculation(exam_session, student, education_level, results):
    """Handle A-Level specific calculations"""
    try:
        # A-Level: Core subjects from combination
        total_grade_points = None
        division = None
        
        # Get student's combination
        combination = student.combination
        if not combination:
            # Delete metrics if no combination
            StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student=student
            ).delete()
            return False
        
        # Get all subjects for this combination
        combo_subjects = CombinationSubject.objects.filter(
            combination=combination
        )
        
        # Separate core and subsidiary subjects
        core_subjects = combo_subjects.filter(role='CORE').values_list('subject_id', flat=True)
        subsidiary_subjects = combo_subjects.filter(role='SUB').values_list('subject_id', flat=True)
        
        # Get results for all combination subjects
        combo_results = results.filter(subject_id__in=list(core_subjects) + list(subsidiary_subjects))
        
        # Calculate points from core subjects (best 3)
        core_points = []
        for result in combo_results.filter(subject_id__in=core_subjects):
            if result.grade_point is not None:
                try:
                    gp = Decimal(str(result.grade_point))
                    core_points.append(gp)
                except (InvalidOperation, TypeError):
                    continue
        
        # Need at least 3 core subjects for A-Level
        if len(core_points) < 3:
            # Delete metrics if not enough core subjects
            StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student=student
            ).delete()
            return False
        
        # Take best 3 core subjects
        core_points.sort(reverse=True)
        best_3_core = core_points[:3]
        total_grade_points = sum(best_3_core)
        
        # Add subsidiary subject points (if any)
        subsidiary_points = []
        for result in combo_results.filter(subject_id__in=subsidiary_subjects):
            if result.grade_point is not None:
                try:
                    gp = Decimal(str(result.grade_point))
                    subsidiary_points.append(gp)
                except (InvalidOperation, TypeError):
                    continue
        
        if subsidiary_points:
            # Take best subsidiary
            subsidiary_points.sort(reverse=True)
            total_grade_points += subsidiary_points[0]
        
        # Determine division
        if total_grade_points is not None:
            try:
                points_int = int(total_grade_points)
                division = DivisionScale.objects.filter(
                    education_level=education_level,
                    min_points__lte=points_int,
                    max_points__gte=points_int
                ).first()
            except (ValueError, TypeError):
                division = None
        
        # Calculate basic statistics
        marks_list = [float(r.marks_obtained) for r in results if r.marks_obtained is not None]
        marks_sum = sum(marks_list)
        total_marks = Decimal(str(marks_sum))
        
        subject_count = len(marks_list)
        average_marks = Decimal(str(marks_sum / subject_count)) if subject_count > 0 else Decimal('0.0')
        
        max_score = float(exam_session.exam_type.max_score)
        average_percentage = Decimal(str((float(average_marks) / max_score * 100))) if max_score > 0 else Decimal('0.0')
        
        average_grade = calculate_average_grade(float(average_percentage))
        average_remark = calculate_remark(float(average_percentage))
        
        # Prepare metrics data
        metrics_data = {
            'total_marks': total_marks,
            'average_marks': average_marks,
            'average_percentage': average_percentage,
            'average_grade': average_grade,
            'average_remark': average_remark,
            'total_grade_points': total_grade_points,
            'division': division,
        }
        
        StudentExamMetrics.objects.update_or_create(
            exam_session=exam_session,
            student=student,
            defaults=metrics_data
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error in A-Level calculation for student {student.id}: {str(e)}", exc_info=True)
        return False


def handle_primary_calculation(exam_session, student, results):
    """Handle Primary/Nursery level calculations"""
    try:
        # Calculate basic statistics
        marks_list = [float(r.marks_obtained) for r in results if r.marks_obtained is not None]
        
        if not marks_list:
            # Delete metrics if no marks
            StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student=student
            ).delete()
            return False
        
        marks_sum = sum(marks_list)
        total_marks = Decimal(str(marks_sum))
        
        subject_count = len(marks_list)
        average_marks = Decimal(str(marks_sum / subject_count)) if subject_count > 0 else Decimal('0.0')
        
        max_score = float(exam_session.exam_type.max_score)
        average_percentage = Decimal(str((float(average_marks) / max_score * 100))) if max_score > 0 else Decimal('0.0')
        
        average_grade = calculate_average_grade(float(average_percentage))
        average_remark = calculate_remark(float(average_percentage))
        
        # Prepare metrics data (no grade points or division for Primary/Nursery)
        metrics_data = {
            'total_marks': total_marks,
            'average_marks': average_marks,
            'average_percentage': average_percentage,
            'average_grade': average_grade,
            'average_remark': average_remark,
            'total_grade_points': None,  # No grade points for Primary/Nursery
            'division': None,  # No division for Primary/Nursery
        }
        
        StudentExamMetrics.objects.update_or_create(
            exam_session=exam_session,
            student=student,
            defaults=metrics_data
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error in Primary calculation for student {student.id}: {str(e)}", exc_info=True)
        return False


def calculate_all_positions(exam_session):
    """
    Calculate class and stream positions for all students in an exam session.
    Implements strict no-duplicate positions rule.
    Positions are based on average_percentage.
    
    Rules:
    1. Higher percentage gets better position
    2. If percentages are equal, compare by total_marks
    3. If both are equal, compare by student's registration number (alphabetical)
    4. No duplicate positions allowed
    """
    try:
        # Get all metrics for this exam session, excluding students without metrics
        metrics_list = StudentExamMetrics.objects.filter(
            exam_session=exam_session
        ).select_related('student').exclude(average_percentage__isnull=True)
        
        if not metrics_list.exists():
            # Clear all positions if no metrics
            StudentExamPosition.objects.filter(exam_session=exam_session).delete()
            return
        
        # Sort by multiple criteria:
        # 1. average_percentage (descending)
        # 2. total_marks (descending) as tie-breaker
        # 3. registration_number (ascending) as second tie-breaker
        sorted_metrics = sorted(
            metrics_list,
            key=lambda x: (
                -float(x.average_percentage or 0),
                -float(x.total_marks or 0),
                x.student.registration_number or ""
            )
        )
        
        # Class position calculation with NO DUPLICATES
        position = 1
        previous_metrics = None
        
        for metrics in sorted_metrics:
            # Always assign unique position
            class_position = position
            position += 1
            
            # Update StudentExamPosition
            StudentExamPosition.objects.update_or_create(
                exam_session=exam_session,
                student=metrics.student,
                defaults={'class_position': class_position}
            )
        
        # Handle students with no metrics (null average_percentage)
        null_metrics = StudentExamMetrics.objects.filter(
            exam_session=exam_session,
            average_percentage__isnull=True
        )
        
        for metrics in null_metrics:
            StudentExamPosition.objects.update_or_create(
                exam_session=exam_session,
                student=metrics.student,
                defaults={'class_position': None}
            )
        
        # Stream position calculation (if stream exists) - also NO DUPLICATES
        if exam_session.stream_class:
            # Get metrics for this specific stream
            stream_metrics = StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student__stream_class=exam_session.stream_class
            ).select_related('student').exclude(average_percentage__isnull=True)
            
            if stream_metrics.exists():
                # Sort stream metrics
                sorted_stream_metrics = sorted(
                    stream_metrics,
                    key=lambda x: (
                        -float(x.average_percentage or 0),
                        -float(x.total_marks or 0),
                        x.student.registration_number or ""
                    )
                )
                
                stream_position = 1
                
                for metrics in sorted_stream_metrics:
                    # Always assign unique position
                    stream_pos = stream_position
                    stream_position += 1
                    
                    # Update stream position
                    StudentExamPosition.objects.filter(
                        exam_session=exam_session,
                        student=metrics.student
                    ).update(stream_position=stream_pos)
            
            # Handle stream students with no percentage
            null_stream_metrics = StudentExamMetrics.objects.filter(
                exam_session=exam_session,
                student__stream_class=exam_session.stream_class,
                average_percentage__isnull=True
            )
            
            for metrics in null_stream_metrics:
                StudentExamPosition.objects.filter(
                    exam_session=exam_session,
                    student=metrics.student
                ).update(stream_position=None)
        
        logger.debug(f"Calculated positions for exam session {exam_session.id}")
        
    except Exception as e:
        logger.error(f"Error calculating positions: {str(e)}", exc_info=True)


def calculate_average_grade(average_percentage):
    """
    Calculate average grade based on percentage.
    Returns a string grade (A, B, C, etc.)
    """
    try:
        if average_percentage >= 80:
            return 'A'
        elif average_percentage >= 70:
            return 'B'
        elif average_percentage >= 60:
            return 'C'
        elif average_percentage >= 50:
            return 'D'
        elif average_percentage >= 40:
            return 'E'
        else:
            return 'F'
    except Exception:
        return ''


def calculate_remark(average_percentage):
    """
    Calculate remark based on percentage.
    Returns a string remark.
    """
    try:
        if average_percentage >= 80:
            return 'Excellent'
        elif average_percentage >= 70:
            return 'Very Good'
        elif average_percentage >= 60:
            return 'Good'
        elif average_percentage >= 50:
            return 'Satisfactory'
        elif average_percentage >= 40:
            return 'Fair'
        else:
            return 'Poor'
    except Exception:
        return ''


# Optimized bulk operations signal handler
@receiver(post_save, sender=StudentResult, dispatch_uid="bulk_results_update")
def handle_bulk_results(sender, instance, created, **kwargs):
    """
    Additional handler for bulk operations to ensure all students are updated.
    Optimized to avoid duplicate calculations.
    """
    global _UPDATING_METRICS
    
    if kwargs.get('raw', False) or _UPDATING_METRICS:
        return
    
    try:
        exam_session = instance.exam_session
        education_level = exam_session.class_level.educational_level
        
        # Get all unique affected students
        with transaction.atomic():
            # Get all students with results in this session
            student_ids = StudentResult.objects.filter(
                exam_session=exam_session
            ).values_list('student_id', flat=True).distinct()
            
            # Process students in batches for better performance
            batch_size = 50
            for i in range(0, len(student_ids), batch_size):
                batch = student_ids[i:i + batch_size]
                students = Student.objects.filter(id__in=batch)
                
                for student in students:
                    try:
                        calculate_student_metrics(exam_session, student, education_level)
                    except Exception as e:
                        logger.error(f"Error in bulk update for student {student.id}: {str(e)}", exc_info=True)
                        continue
        
        # Recalculate positions once after all metrics are updated
        calculate_all_positions(exam_session)
        
    except Exception as e:
        logger.error(f"Error in bulk results update: {str(e)}", exc_info=True)


# REMOVE the problematic update_metrics_timestamp signal entirely
# @receiver(post_save, sender=StudentExamMetrics)
# def update_metrics_timestamp(sender, instance, **kwargs):
#     """Update calculated_at timestamp when metrics are saved."""
#     from django.utils import timezone
#     if not kwargs.get('raw', False):
#         instance.calculated_at = timezone.now()
#         instance.save(update_fields=['calculated_at'])


# Signal to handle when a student's combination changes
@receiver(post_save, sender=Student)
def update_student_combination_metrics(sender, instance, **kwargs):
    """
    Update metrics when student's combination changes.
    Only affects A-Level students.
    """
    global _UPDATING_METRICS
    
    if kwargs.get('raw', False) or _UPDATING_METRICS:
        return
    
    try:
        # Only process if combination changed and student is A-Level
        if instance.combination and instance.class_level:
            education_level = instance.class_level.educational_level
            if education_level and education_level.code and education_level.code.upper() == 'A_LEVEL':
                # Get all exam sessions for this student
                exam_sessions = ExamSession.objects.filter(
                    class_level=instance.class_level,
                    results__student=instance
                ).distinct()
                
                for exam_session in exam_sessions:
                    calculate_student_metrics(exam_session, instance, education_level)
                    calculate_all_positions(exam_session)
                    
    except Exception as e:
        logger.error(f"Error updating student combination metrics: {str(e)}", exc_info=True)


# Utility function for manual recalculation
def recalculate_all_metrics_for_session(exam_session_id):
    """
    Manually recalculate all metrics and positions for an exam session.
    Useful for fixing data or after major changes.
    """
    from django.db import transaction
    
    try:
        from .models import ExamSession
        exam_session = ExamSession.objects.get(id=exam_session_id)
        
        with transaction.atomic():
            # Clear existing metrics and positions
            StudentExamMetrics.objects.filter(exam_session=exam_session).delete()
            StudentExamPosition.objects.filter(exam_session=exam_session).delete()
            
            # Get all students with results in this session
            student_ids = exam_session.results.values_list(
                'student_id', flat=True
            ).distinct()
            
            students = Student.objects.filter(id__in=student_ids)
            education_level = exam_session.class_level.educational_level
            
            # Calculate metrics for each student
            for student in students:
                calculate_student_metrics(exam_session, student, education_level)
            
            # Calculate positions
            calculate_all_positions(exam_session)
            
            return True, f"Recalculated metrics for {students.count()} students"
            
    except Exception as e:
        logger.error(f"Error recalculating metrics for session {exam_session_id}: {str(e)}", exc_info=True)
        return False, f"Error recalculating metrics: {str(e)}"


# Add a signal to handle when grading scales change
@receiver(post_save, sender=GradingScale)
def update_grading_scale_metrics(sender, instance, **kwargs):
    """
    Update all metrics when grading scales change.
    This is important because grade points might change.
    """
    global _UPDATING_METRICS
    
    if kwargs.get('raw', False) or _UPDATING_METRICS:
        return
    
    try:
        education_level = instance.education_level
        
        # Find all exam sessions for this education level
        exam_sessions = ExamSession.objects.filter(
            class_level__educational_level=education_level
        ).distinct()
        
        for exam_session in exam_sessions:
            # Get all students in this exam session
            student_ids = exam_session.results.values_list(
                'student_id', flat=True
            ).distinct()
            
            students = Student.objects.filter(id__in=student_ids)
            
            for student in students:
                calculate_student_metrics(exam_session, student, education_level)
            
            calculate_all_positions(exam_session)
            
    except Exception as e:
        logger.error(f"Error updating metrics for grading scale changes: {str(e)}", exc_info=True)