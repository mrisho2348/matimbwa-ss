from django.db import transaction
from .models import ExamSession, StudentExamMetrics, StudentExamPosition


def recalculate_all_metrics_for_session(exam_session_id):
    """
    Manually recalculate all metrics and positions for an exam session.
    Useful for fixing data or after major changes.
    """
    from .signals import calculate_student_metrics, calculate_all_positions
    
    try:
        exam_session = ExamSession.objects.get(id=exam_session_id)
        
        with transaction.atomic():
            # Clear existing metrics and positions
            StudentExamMetrics.objects.filter(exam_session=exam_session).delete()
            StudentExamPosition.objects.filter(exam_session=exam_session).delete()
            
            # Get all students with results in this session
            student_ids = exam_session.results.values_list(
                'student_id', flat=True
            ).distinct()
            
            from students.models import Student
            students = Student.objects.filter(id__in=student_ids)
            
            education_level = exam_session.class_level.educational_level
            
            # Calculate metrics for each student
            for student in students:
                calculate_student_metrics(exam_session, student, education_level)
            
            # Calculate positions
            calculate_all_positions(exam_session)
            
            return True, f"Recalculated metrics for {students.count()} students"
            
    except Exception as e:
        return False, f"Error recalculating metrics: {str(e)}"


def bulk_recalculate_metrics(exam_session_ids):
    """
    Recalculate metrics for multiple exam sessions.
    """
    results = []
    for session_id in exam_session_ids:
        success, message = recalculate_all_metrics_for_session(session_id)
        results.append({
            'exam_session_id': session_id,
            'success': success,
            'message': message
        })
    return results