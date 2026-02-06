# attendance/views.py
import json
import csv
from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
import pandas as pd
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from students.models import AttendanceSession, Student,StreamClass, StudentAttendance
from core.models import ClassLevel, Subject
from accounts.models import Staffs
from django.contrib import messages
from django.utils import timezone
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.shortcuts import redirect
from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration
from django.conf import settings
from django.urls import reverse



class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser





class AttendanceSessionListView(AdminRequiredMixin, ListView):
    model = AttendanceSession
    template_name = 'admin/attendance/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'class_level', 'stream', 'subject'
        ).order_by('-date', '-id')
        
        # Apply filters
        date_filter = self.request.GET.get('date')
        class_filter = self.request.GET.get('class_level')
        stream_filter = self.request.GET.get('stream')
        type_filter = self.request.GET.get('attendance_type')
        
        if date_filter:
            queryset = queryset.filter(date=date_filter)
        if class_filter:
            queryset = queryset.filter(class_level_id=class_filter)
        if stream_filter:
            queryset = queryset.filter(stream_id=stream_filter)
        if type_filter:
            queryset = queryset.filter(attendance_type=type_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['class_levels'] = ClassLevel.objects.all()
        context['filter_date'] = self.request.GET.get('date', '')
        context['filter_class'] = self.request.GET.get('class_level', '')
        context['filter_stream'] = self.request.GET.get('stream', '')
        context['filter_type'] = self.request.GET.get('attendance_type', '')
        return context


# attendance/views.py
class CreateAttendanceSessionView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/attendance/create_session.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get today's date and related dates
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        context['class_levels'] = ClassLevel.objects.all()
        context['today'] = today
        context['yesterday'] = yesterday
        context['tomorrow'] = tomorrow
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class GetAttendanceSessionsAPI(AdminRequiredMixin, View):
    def get(self, request):
        try:
            # Get filter parameters
            date_filter = request.GET.get('date')
            class_filter = request.GET.get('class_level')
            stream_filter = request.GET.get('stream')
            type_filter = request.GET.get('attendance_type')
            
            # Build queryset
            queryset = AttendanceSession.objects.select_related(
                'class_level', 'stream', 'subject'
            )
            
            if date_filter:
                queryset = queryset.filter(date=date_filter)
            if class_filter:
                queryset = queryset.filter(class_level_id=class_filter)
            if stream_filter:
                queryset = queryset.filter(stream_id=stream_filter)
            if type_filter:
                queryset = queryset.filter(attendance_type=type_filter)
            
            sessions_data = []
            overall_stats = {'present': 0, 'absent': 0, 'late': 0, 'excused': 0, 'total': 0}
            
            for session in queryset.order_by('-date', '-id')[:50]:  # Limit to 50 sessions
                # Get attendance statistics for this session
                attendance_stats = StudentAttendance.objects.filter(
                    attendance_session=session
                ).aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                # Update overall stats
                overall_stats['present'] += attendance_stats['present'] or 0
                overall_stats['absent'] += attendance_stats['absent'] or 0
                overall_stats['late'] += attendance_stats['late'] or 0
                overall_stats['excused'] += attendance_stats['excused'] or 0
                overall_stats['total'] += attendance_stats['total'] or 0
                
                sessions_data.append({
                    'id': session.id,
                    'date': session.date.strftime('%Y-%m-%d'),
                    'attendance_type': session.attendance_type,
                    'attendance_type_display': session.get_attendance_type_display(),
                    'class_level_name': session.class_level.name,
                    'class_level_id': session.class_level.id,  # ADD THIS
                    'stream_name': session.stream.stream_letter if session.stream else 'All',
                    'stream_id': session.stream.id if session.stream else None,  # ADD THIS
                    'subject_name': session.subject.name if session.subject else 'Class Attendance',
                    'subject_id': session.subject.id if session.subject else None,  # ADD THIS
                    'period': session.period,
                    'stats': {
                        'present': attendance_stats['present'] or 0,
                        'absent': attendance_stats['absent'] or 0,
                        'late': attendance_stats['late'] or 0,
                        'excused': attendance_stats['excused'] or 0,
                        'total': attendance_stats['total'] or 0,
                    }
                })
            
            return JsonResponse({
                'success': True,
                'sessions': sessions_data,
                'stats': overall_stats,
                'count': len(sessions_data)
            })
            
        except Exception as e:
            import traceback
            print(f"Error in GetAttendanceSessionsAPI: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

            



@method_decorator(csrf_exempt, name='dispatch')
class CreateAttendanceSessionAPI(AdminRequiredMixin, View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'create_session':
                # Validate required fields (removed teacher from required)
                required_fields = ['date', 'attendance_type', 'class_level', 'stream']
                for field in required_fields:
                    if field not in data or not data[field]:
                        return JsonResponse({
                            'success': False,
                            'message': f'{field.replace("_", " ").title()} is required'
                        })
                
                # Create attendance session (remove teacher field)
                attendance_session = AttendanceSession.objects.create(
                    date=data['date'],
                    attendance_type=data['attendance_type'],
                    class_level_id=data['class_level'],
                    stream_id=data['stream'],
                    subject_id=data.get('subject'),
                    period=data.get('period')
                )
                
                # Create student attendance records
                student_attendance_data = data.get('student_attendance', {})
                student_attendance_objects = []
                
                for student_id, attendance_data in student_attendance_data.items():
                    student_attendance_objects.append(
                        StudentAttendance(
                            attendance_session=attendance_session,
                            student_id=student_id,
                            status=attendance_data.get('status', 'A'),  # Default to Absent
                            remark=attendance_data.get('remark', '')
                        )
                    )
                
                # Bulk create student attendance records
                if student_attendance_objects:
                    StudentAttendance.objects.bulk_create(student_attendance_objects)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Attendance session created successfully',
                    'session_id': attendance_session.id
                })
            
            elif action == 'update_session':
                session_id = data.get('session_id')
                if not session_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Session ID is required'
                    })
                
                attendance_session = get_object_or_404(AttendanceSession, id=session_id)
                
                # Update attendance session (removed teacher field)
                for field in ['date', 'attendance_type', 'period']:
                    if field in data:
                        setattr(attendance_session, field, data[field])
                
                if 'class_level' in data:
                    attendance_session.class_level_id = data['class_level']
                if 'stream' in data:
                    attendance_session.stream_id = data['stream']
                if 'subject' in data:
                    attendance_session.subject_id = data['subject']
                # Removed teacher field
                
                attendance_session.save()
                
                # Update student attendance if provided
                if 'student_attendance' in data:
                    student_attendance_data = data['student_attendance']
                    for student_id, attendance_data in student_attendance_data.items():
                        StudentAttendance.objects.update_or_create(
                            attendance_session=attendance_session,
                            student_id=student_id,
                            defaults={
                                'status': attendance_data.get('status', 'A'),
                                'remark': attendance_data.get('remark', '')
                            }
                        )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Attendance session updated successfully'
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
        

@method_decorator(csrf_exempt, name='dispatch')
class AttendanceSessionDetailAPI(AdminRequiredMixin, View):
    def get(self, request, session_id):  # Add session_id parameter here
        try:
            # Remove this line since session_id comes from URL parameter
            # session_id = request.GET.get('session_id')
            
            attendance_session = get_object_or_404(
                AttendanceSession.objects.select_related(
                    'class_level', 'stream', 'subject'
                ),
                id=session_id
            )
            
            # Get student attendance for this session
            student_attendances = StudentAttendance.objects.select_related('student').filter(
                attendance_session=attendance_session
            )
            
            # Prepare HTML content for modal
            html_content = f"""
            <div class="attendance-details">
                <div class="row mb-4">
                    <div class="col-md-6">
                        <h5>Session Information</h5>
                        <table class="table table-sm">
                            <tr>
                                <th>Date:</th>
                                <td>{attendance_session.date}</td>
                            </tr>
                            <tr>
                                <th>Type:</th>
                                <td><span class="badge badge-{'info' if attendance_session.attendance_type == 'CLASS' else 'success'}">
                                    {attendance_session.get_attendance_type_display()}
                                </span></td>
                            </tr>
                            <tr>
                                <th>Class:</th>
                                <td>{attendance_session.class_level.name} - {attendance_session.stream.stream_letter if attendance_session.stream else 'All'}</td>
                            </tr>
                            <tr>
                                <th>Subject:</th>
                                <td>{attendance_session.subject.name if attendance_session.subject else 'N/A'}</td>
                            </tr>
                            <tr>
                                <th>Period:</th>
                                <td>{attendance_session.period or 'N/A'}</td>
                            </tr>                            
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h5>Attendance Statistics</h5>
                        <div class="row text-center">
                            <div class="col-3">
                                <div class="stat-card stat-present p-2 mb-2">
                                    <div class="stat-number">{student_attendances.filter(status='P').count()}</div>
                                    <div class="stat-label">Present</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-card stat-absent p-2 mb-2">
                                    <div class="stat-number">{student_attendances.filter(status='A').count()}</div>
                                    <div class="stat-label">Absent</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-card stat-late p-2 mb-2">
                                    <div class="stat-number">{student_attendances.filter(status='L').count()}</div>
                                    <div class="stat-label">Late</div>
                                </div>
                            </div>
                            <div class="col-3">
                                <div class="stat-card stat-excused p-2 mb-2">
                                    <div class="stat-number">{student_attendances.filter(status='E').count()}</div>
                                    <div class="stat-label">Excused</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <h5>Student Attendance</h5>
                <div class="table-responsive">
                    <table class="table table-bordered table-sm">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Student</th>
                                <th>Admission No.</th>
                                <th>Status</th>
                                <th>Remark</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for i, attendance in enumerate(student_attendances, 1):
                status_badge_class = {
                    'P': 'badge-success',
                    'A': 'badge-danger',
                    'L': 'badge-warning',
                    'E': 'badge-info'
                }.get(attendance.status, 'badge-secondary')
                
                status_text = {
                    'P': 'Present',
                    'A': 'Absent',
                    'L': 'Late',
                    'E': 'Excused'
                }.get(attendance.status, 'Unknown')
                
                html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td>{attendance.student.full_name}</td>
                                <td>{attendance.student.registration_number}</td>
                                <td><span class="badge {status_badge_class}">{status_text}</span></td>
                                <td>{attendance.remark or '-'}</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
            """
            
            return JsonResponse({
                'success': True,
                'html': html_content
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class DeleteAttendanceSessionAPI(AdminRequiredMixin, View):
    def post(self, request, session_id):
        try:
            attendance_session = get_object_or_404(AttendanceSession, id=session_id)
            attendance_session.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance session deleted successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


# Data Loading APIs
@method_decorator(csrf_exempt, name='dispatch')
class GetStreamsForClassAPI(AdminRequiredMixin, View):
    def get(self, request, class_id):
        try:
            streams = StreamClass.objects.filter(class_level_id=class_id, is_active=True)
            streams_data = [{'id': s.id, 'name': s.stream_letter} for s in streams]
            
            return JsonResponse({
                'success': True,
                'streams': streams_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class GetSubjectsForClassAPI(AdminRequiredMixin, View):
    def get(self, request, class_id):
        try:
            class_level = get_object_or_404(ClassLevel, id=class_id)
            subjects = Subject.objects.filter(
                educational_level=class_level.educational_level,
                is_active=True
            )
            subjects_data = [{'id': s.id, 'name': s.name} for s in subjects]
            
            return JsonResponse({
                'success': True,
                'subjects': subjects_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class GetStudentsByClassStreamAPI(AdminRequiredMixin, View):
    def get(self, request, class_id, stream_id):
        try:
            # Correct field names based on your Student model
            students = Student.objects.filter(
                class_level_id=class_id,
                stream_class_id=stream_id,
                is_active=True
            )
            
            students_data = []
            for student in students:
                try:
                    profile_picture_url = student.profile_pic.url if student.profile_pic else None
                except:
                    profile_picture_url = None
                
                students_data.append({
                    'id': student.id,
                    'full_name': student.full_name,
                    'admission_number':  student.registration_number or "",
                    'profile_picture': profile_picture_url
                })
            
            return JsonResponse({
                'success': True,
                'students': students_data,
                'count': len(students_data)
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=400)






class DailyAttendanceReportView(AdminRequiredMixin, TemplateView):
    """Detailed daily attendance report with filters and statistics"""
    template_name = 'admin/attendance/reports/daily_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        report_date = self.request.GET.get('date', '')
        class_filter = self.request.GET.get('class_level', '')
        stream_filter = self.request.GET.get('stream', '')
        attendance_type = self.request.GET.get('attendance_type', 'ALL')
        view_mode = self.request.GET.get('view', 'summary')  # summary or detailed
        
        # Set default date to today if not provided
        if not report_date:
            report_date = timezone.now().date().strftime('%Y-%m-%d')
        
        try:
            date_obj = datetime.strptime(report_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            date_obj = timezone.now().date()
            report_date = date_obj.strftime('%Y-%m-%d')
        
        # Get all attendance sessions for the date
        attendance_sessions = AttendanceSession.objects.filter(
            date=date_obj
        ).select_related(
            'class_level', 'stream', 'subject'
        ).order_by('class_level__name', 'stream__stream_letter', 'period')
        
        # Apply additional filters
        if class_filter:
            attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
        if stream_filter:
            attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
        if attendance_type and attendance_type != 'ALL':
            attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
        
        # Prepare data structure for the report
        class_levels_data = {}
        total_stats = {
            'sessions': 0,
            'students': 0,
            'present': 0,
            'absent': 0,
            'late': 0,
            'excused': 0,
            'attendance_rate': 0
        }
        
        for session in attendance_sessions:
            class_key = f"{session.class_level.name}_{session.stream.stream_letter}"
            
            if class_key not in class_levels_data:
                class_levels_data[class_key] = {
                    'class_level': session.class_level,
                    'stream': session.stream,
                    'sessions': [],
                    'stats': {
                        'total_sessions': 0,
                        'total_students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                }
            
            # Get student attendance for this session
            student_attendances = StudentAttendance.objects.filter(
                attendance_session=session
            ).select_related('student')
            
            # Calculate session statistics
            session_stats = student_attendances.aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='P')),
                absent=Count('id', filter=Q(status='A')),
                late=Count('id', filter=Q(status='L')),
                excused=Count('id', filter=Q(status='E'))
            )
            
            session_rate = 0
            if session_stats['total'] and session_stats['total'] > 0:
                session_rate = round((session_stats['present'] / session_stats['total']) * 100, 2)
            
            # Add session to class data
            session_data = {
                'session': session,
                'student_attendances': student_attendances,
                'stats': session_stats,
                'attendance_rate': session_rate,
                'time': session.created_at.strftime('%I:%M %p') if session.created_at else 'N/A'
            }
            
            class_levels_data[class_key]['sessions'].append(session_data)
            
            # Update class stats
            class_stats = class_levels_data[class_key]['stats']
            class_stats['total_sessions'] += 1
            class_stats['total_students'] += session_stats['total'] or 0
            class_stats['present'] += session_stats['present'] or 0
            class_stats['absent'] += session_stats['absent'] or 0
            class_stats['late'] += session_stats['late'] or 0
            class_stats['excused'] += session_stats['excused'] or 0
            
            # Update total stats
            total_stats['sessions'] += 1
            total_stats['students'] += session_stats['total'] or 0
            total_stats['present'] += session_stats['present'] or 0
            total_stats['absent'] += session_stats['absent'] or 0
            total_stats['late'] += session_stats['late'] or 0
            total_stats['excused'] += session_stats['excused'] or 0
        
        # Calculate attendance rates
        for class_data in class_levels_data.values():
            class_stats = class_data['stats']
            if class_stats['total_students'] > 0:
                class_stats['attendance_rate'] = round(
                    (class_stats['present'] / class_stats['total_students']) * 100, 2
                )
        
        if total_stats['students'] > 0:
            total_stats['attendance_rate'] = round(
                (total_stats['present'] / total_stats['students']) * 100, 2
            )
        
        # Get student summary for detailed view
        student_summary = {}
        if view_mode == 'detailed':
            # Get all students with attendance for the day
            all_attendance = StudentAttendance.objects.filter(
                attendance_session__date=date_obj
            ).select_related('student', 'attendance_session')
            
            for attendance in all_attendance:
                student_id = attendance.student_id
                if student_id not in student_summary:
                    student_summary[student_id] = {
                        'student': attendance.student,
                        'sessions': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'classes': set(),
                        'attendance_rate': 0
                    }
                
                student_data = student_summary[student_id]
                student_data['sessions'] += 1
                
                if attendance.status == 'P':
                    student_data['present'] += 1
                elif attendance.status == 'A':
                    student_data['absent'] += 1
                elif attendance.status == 'L':
                    student_data['late'] += 1
                elif attendance.status == 'E':
                    student_data['excused'] += 1
                
                # Track classes attended
                class_name = f"{attendance.attendance_session.class_level.name} {attendance.attendance_session.stream.stream_letter}"
                student_data['classes'].add(class_name)
                
                # Calculate attendance rate
                if student_data['sessions'] > 0:
                    student_data['attendance_rate'] = round(
                        (student_data['present'] / student_data['sessions']) * 100, 2
                    )
                
                # Convert set to list for template
                student_data['classes_list'] = list(student_data['classes'])
        
        # Sort class data
        sorted_class_data = sorted(
            class_levels_data.values(),
            key=lambda x: (x['class_level'].name, x['stream'].stream_letter)
        )
        
        # Sort student summary by name
        sorted_student_summary = sorted(
            student_summary.values(),
            key=lambda x: (x['student'].class_level.name if x['student'].class_level else '', 
                          x['student'].last_name, x['student'].first_name)
        ) if view_mode == 'detailed' else []
        
        # Prepare context
        context.update({
            'report_date': report_date,
            'date_obj': date_obj,
            'class_levels_data': sorted_class_data,
            'student_summary': sorted_student_summary,
            'total_stats': total_stats,
            'class_levels': ClassLevel.objects.all(),
            'filter_class': class_filter,
            'filter_stream': stream_filter,
            'filter_type': attendance_type,
            'filter_view': view_mode,
            'attendance_types': [
                ('ALL', 'All Types'),
                ('CLASS', 'Class Wise'),
                ('SUBJECT', 'Subject Wise')
            ],
            'view_modes': [
                ('summary', 'Summary View'),
                ('detailed', 'Detailed View')
            ],
            'formatted_date': date_obj.strftime('%B %d, %Y'),
            'day_name': date_obj.strftime('%A'),
            'total_classes': len(class_levels_data),
            'has_data': len(attendance_sessions) > 0,
        })
        
        # Get streams for selected class
        if class_filter:
            context['streams'] = StreamClass.objects.filter(
                class_level_id=class_filter, 
                is_active=True
            )
        else:
            context['streams'] = StreamClass.objects.none()
        
        return context




# Update the ExportDailyAttendancePDFView context preparation

class ExportDailyAttendancePDFView(AdminRequiredMixin, View):
    """Export daily attendance report as PDF"""
    
    def get(self, request):
        try:
            # Get filter parameters from request
            report_date = request.GET.get('date', '')
            class_filter = request.GET.get('class_level', '')
            stream_filter = request.GET.get('stream', '')
            attendance_type = request.GET.get('attendance_type', 'ALL')
            view_mode = request.GET.get('view', 'summary')  # Get view mode
            
            # Set default date to today if not provided
            if not report_date:
                report_date = timezone.now().date().strftime('%Y-%m-%d')
            
            try:
                date_obj = datetime.strptime(report_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                date_obj = timezone.now().date()
                report_date = date_obj.strftime('%Y-%m-%d')
            
            # Build queryset with filters
            attendance_sessions = AttendanceSession.objects.filter(
                date=date_obj
            ).select_related(
                'class_level', 'stream', 'subject'
            ).order_by('class_level__name', 'stream__stream_letter', 'period')
            
            # Apply additional filters
            if class_filter:
                attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
            if stream_filter:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Check if data exists
            if not attendance_sessions.exists():
                raise Exception(f"No attendance data found for {date_obj.strftime('%B %d, %Y')} with selected filters")
            
            # Prepare data structure
            class_levels_data = {}
            total_stats = {
                'sessions': 0,
                'students': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'excused': 0,
                'attendance_rate': 0
            }
            
            # Process each session
            for session in attendance_sessions:
                class_key = f"{session.class_level.name}_{session.stream.stream_letter if session.stream else 'ALL'}"
                
                if class_key not in class_levels_data:
                    class_levels_data[class_key] = {
                        'class_level': session.class_level,
                        'stream': session.stream,
                        'sessions': [],
                        'stats': {
                            'total_sessions': 0,
                            'total_students': 0,
                            'present': 0,
                            'absent': 0,
                            'late': 0,
                            'excused': 0,
                            'attendance_rate': 0
                        }
                    }
                
                # Get attendance for this session
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                )
                
                # Calculate statistics with proper defaults
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                # Ensure all values are integers (not None)
                for key in ['total', 'present', 'absent', 'late', 'excused']:
                    session_stats[key] = session_stats[key] or 0
                
                # Calculate attendance rate
                session_rate = 0
                if session_stats['total'] > 0:
                    session_rate = round((session_stats['present'] / session_stats['total']) * 100, 2)
                
                # Add session data
                session_data = {
                    'session': session,
                    'stats': session_stats,
                    'attendance_rate': session_rate,
                    'time': session.created_at.strftime('%I:%M %p') if session.created_at else 'N/A'
                }
                
                class_levels_data[class_key]['sessions'].append(session_data)
                
                # Update class statistics
                class_stats = class_levels_data[class_key]['stats']
                class_stats['total_sessions'] += 1
                class_stats['total_students'] += session_stats['total']
                class_stats['present'] += session_stats['present']
                class_stats['absent'] += session_stats['absent']
                class_stats['late'] += session_stats['late']
                class_stats['excused'] += session_stats['excused']
                
                # Update total statistics
                total_stats['sessions'] += 1
                total_stats['students'] += session_stats['total']
                total_stats['present'] += session_stats['present']
                total_stats['absent'] += session_stats['absent']
                total_stats['late'] += session_stats['late']
                total_stats['excused'] += session_stats['excused']
            
            # Calculate attendance rates for each class
            for class_key, class_data in class_levels_data.items():
                class_stats = class_data['stats']
                if class_stats['total_students'] > 0:
                    class_stats['attendance_rate'] = round(
                        (class_stats['present'] / class_stats['total_students']) * 100, 2
                    )
            
            # Calculate overall attendance rate
            if total_stats['students'] > 0:
                total_stats['attendance_rate'] = round(
                    (total_stats['present'] / total_stats['students']) * 100, 2
                )
            
            # Sort class data
            sorted_class_data = sorted(
                class_levels_data.values(),
                key=lambda x: (x['class_level'].name, x['stream'].stream_letter if x['stream'] else '')
            )
            
            # Get student summary for detailed view if needed
            student_summary = []
            if view_mode in ['summary', 'both', 'detailed']:
                # Get all students with attendance for the day
                all_attendance = StudentAttendance.objects.filter(
                    attendance_session__date=date_obj
                ).select_related('student', 'attendance_session')
                
                # Apply class filter if specified
                if class_filter:
                    all_attendance = all_attendance.filter(
                        attendance_session__class_level_id=class_filter
                    )
                
                # Apply stream filter if specified
                if stream_filter:
                    all_attendance = all_attendance.filter(
                        attendance_session__stream_id=stream_filter
                    )
                
                student_data_dict = {}
                for attendance in all_attendance:
                    student_id = attendance.student_id
                    if student_id not in student_data_dict:
                        student_data_dict[student_id] = {
                            'student': attendance.student,
                            'sessions': 0,
                            'present': 0,
                            'absent': 0,
                            'late': 0,
                            'excused': 0,
                            'classes': set(),
                            'attendance_rate': 0
                        }
                    
                    student_data = student_data_dict[student_id]
                    student_data['sessions'] += 1
                    
                    if attendance.status == 'P':
                        student_data['present'] += 1
                    elif attendance.status == 'A':
                        student_data['absent'] += 1
                    elif attendance.status == 'L':
                        student_data['late'] += 1
                    elif attendance.status == 'E':
                        student_data['excused'] += 1
                    
                    # Track classes attended
                    class_name = f"{attendance.attendance_session.class_level.name} {attendance.attendance_session.stream.stream_letter if attendance.attendance_session.stream else ''}"
                    student_data['classes'].add(class_name.strip())
                    
                    # Calculate attendance rate
                    if student_data['sessions'] > 0:
                        student_data['attendance_rate'] = round(
                            (student_data['present'] / student_data['sessions']) * 100, 2
                        )
                    
                    # Convert set to list for template
                    student_data['classes_list'] = list(student_data['classes'])
                
                # Convert to list and sort
                student_summary = sorted(
                    student_data_dict.values(),
                    key=lambda x: (x['student'].class_level.name if x['student'].class_level else '', 
                                  x['student'].last_name, x['student'].first_name)
                )
            
            # Get school information
            from django.conf import settings
            school_name = getattr(settings, 'SCHOOL_NAME', 'Your School Name')
            school_address = getattr(settings, 'SCHOOL_ADDRESS', 'Your School Address')
            
            # Prepare context
            context = {
                'report_date': report_date,
                'date_obj': date_obj,
                'formatted_date': date_obj.strftime('%B %d, %Y'),
                'day_name': date_obj.strftime('%A'),
                'class_levels_data': sorted_class_data,
                'student_summary': student_summary,
                'total_stats': total_stats,
                'total_classes': len(class_levels_data),
                'school_name': school_name,
                'school_address': school_address,
                'generation_date': timezone.now().strftime('%B %d, %Y %I:%M %p'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'filter_class_name': '',
                'filter_stream_name': '',
                'filter_type_name': '',
                'filter_view': view_mode,
                'has_data': True,
            }
            
            # Add filter information if filters were applied
            if class_filter:
                try:
                    class_obj = ClassLevel.objects.get(id=class_filter)
                    context['filter_class_name'] = class_obj.name
                except ClassLevel.DoesNotExist:
                    pass
            
            if stream_filter:
                try:
                    stream_obj = StreamClass.objects.get(id=stream_filter)
                    context['filter_stream_name'] = stream_obj.stream_letter
                except StreamClass.DoesNotExist:
                    pass
            
            if attendance_type != 'ALL':
                type_display = dict(AttendanceSession.ATTENDANCE_TYPE_CHOICES).get(attendance_type, attendance_type)
                context['filter_type_name'] = type_display
            
            # Render the HTML template
            html_string = render_to_string('admin/attendance/reports/daily_report_pdf.html', context)
            
            # Configure fonts for PDF generation
            font_config = FontConfiguration()
            
            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = html.write_pdf(font_config=font_config)
            
            # Create HTTP response
            response = HttpResponse(pdf_file, content_type='application/pdf')
            
            # Generate filename
            filename = f"daily_attendance_{report_date}"
            if context['filter_class_name']:
                filename += f"_{context['filter_class_name'].replace(' ', '_')}"
            if context['filter_stream_name']:
                filename += f"_Stream_{context['filter_stream_name']}"
            if view_mode != 'summary':
                filename += f"_{view_mode}_view"
            filename += ".pdf"
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error generating PDF: {e}")
            print(traceback.format_exc())
            
            # Store error in session and redirect back
            messages.error(request, f"Failed to generate PDF: {str(e)}")
            return redirect('attendance_report_daily')


# attendance/views.py - Add this class

class MonthlyAttendanceReportView(AdminRequiredMixin, TemplateView):
    """Monthly attendance report with filtering options"""
    template_name = 'admin/attendance/reports/monthly_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        month = self.request.GET.get('month', timezone.now().month)
        year = self.request.GET.get('year', timezone.now().year)
        class_filter = self.request.GET.get('class_level', '')
        stream_filter = self.request.GET.get('stream', '')
        attendance_type = self.request.GET.get('attendance_type', 'ALL')
        view_mode = self.request.GET.get('view', 'summary')  # summary, detailed, both
        
        # Convert month and year to integers
        try:
            month = int(month)
            year = int(year)
        except (ValueError, TypeError):
            month = timezone.now().month
            year = timezone.now().year
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get attendance sessions for the month
        attendance_sessions = AttendanceSession.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related(
            'class_level', 'stream', 'subject'
        ).order_by('date', 'class_level__name', 'stream__stream_letter')
        
        # Apply additional filters
        if class_filter:
            attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
        if stream_filter:
            attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
        if attendance_type and attendance_type != 'ALL':
            attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
        
        # Prepare data structures
        daily_data = {}
        class_data = {}
        student_data = {}
        
        total_stats = {
            'days': 0,
            'sessions': 0,
            'students': 0,
            'present': 0,
            'absent': 0,
            'late': 0,
            'excused': 0,
            'attendance_rate': 0
        }
        
        # Process each attendance session
        for session in attendance_sessions:
            date_str = session.date.strftime('%Y-%m-%d')
            class_key = f"{session.class_level.name}_{session.stream.stream_letter if session.stream else 'ALL'}"
            
            # Initialize daily data if not exists
            if date_str not in daily_data:
                daily_data[date_str] = {
                    'date': session.date,
                    'day_name': session.date.strftime('%A'),
                    'sessions': 0,
                    'students': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'attendance_rate': 0,
                    'class_stats': {}
                }
            
            # Initialize class data if not exists
            if class_key not in class_data:
                class_data[class_key] = {
                    'class_level': session.class_level,
                    'stream': session.stream,
                    'days': set(),
                    'sessions': 0,
                    'students': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'attendance_rate': 0
                }
            
            # Get attendance records for this session
            student_attendances = StudentAttendance.objects.filter(
                attendance_session=session
            )
            
            # Calculate session statistics
            session_stats = student_attendances.aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='P')),
                absent=Count('id', filter=Q(status='A')),
                late=Count('id', filter=Q(status='L')),
                excused=Count('id', filter=Q(status='E'))
            )
            
            # Ensure all values are integers
            for key in ['total', 'present', 'absent', 'late', 'excused']:
                session_stats[key] = session_stats[key] or 0
            
            # Update daily statistics
            daily_data[date_str]['sessions'] += 1
            daily_data[date_str]['students'] += session_stats['total']
            daily_data[date_str]['present'] += session_stats['present']
            daily_data[date_str]['absent'] += session_stats['absent']
            daily_data[date_str]['late'] += session_stats['late']
            daily_data[date_str]['excused'] += session_stats['excused']
            
            # Update class statistics
            class_data[class_key]['days'].add(session.date)
            class_data[class_key]['sessions'] += 1
            class_data[class_key]['students'] += session_stats['total']
            class_data[class_key]['present'] += session_stats['present']
            class_data[class_key]['absent'] += session_stats['absent']
            class_data[class_key]['late'] += session_stats['late']
            class_data[class_key]['excused'] += session_stats['excused']
            
            # Update total statistics
            total_stats['sessions'] += 1
            total_stats['students'] += session_stats['total']
            total_stats['present'] += session_stats['present']
            total_stats['absent'] += session_stats['absent']
            total_stats['late'] += session_stats['late']
            total_stats['excused'] += session_stats['excused']
            
            # Track individual student attendance for detailed view
            if view_mode in ['detailed', 'both']:
                for attendance in student_attendances.select_related('student'):
                    student_id = attendance.student_id
                    if student_id not in student_data:
                        student_data[student_id] = {
                            'student': attendance.student,
                            'days': set(),
                            'sessions': 0,
                            'present': 0,
                            'absent': 0,
                            'late': 0,
                            'excused': 0,
                            'attendance_rate': 0
                        }
                    
                    student = student_data[student_id]
                    student['days'].add(session.date)
                    student['sessions'] += 1
                    
                    if attendance.status == 'P':
                        student['present'] += 1
                    elif attendance.status == 'A':
                        student['absent'] += 1
                    elif attendance.status == 'L':
                        student['late'] += 1
                    elif attendance.status == 'E':
                        student['excused'] += 1
        
        # Calculate attendance rates
        total_stats['days'] = len(daily_data)
        if total_stats['students'] > 0:
            total_stats['attendance_rate'] = round(
                (total_stats['present'] / total_stats['students']) * 100, 2
            )
        
        # Calculate daily attendance rates
        for date_str, day_data in daily_data.items():
            if day_data['students'] > 0:
                day_data['attendance_rate'] = round(
                    (day_data['present'] / day_data['students']) * 100, 2
                )
        
        # Calculate class attendance rates and convert days set to count
        for class_key, cdata in class_data.items():
            cdata['days'] = len(cdata['days'])
            if cdata['students'] > 0:
                cdata['attendance_rate'] = round(
                    (cdata['present'] / cdata['students']) * 100, 2
                )
        
        # Calculate student attendance rates
        for student_id, sdata in student_data.items():
            sdata['days'] = len(sdata['days'])
            if sdata['sessions'] > 0:
                sdata['attendance_rate'] = round(
                    (sdata['present'] / sdata['sessions']) * 100, 2
                )
        
        # Sort data
        sorted_daily_data = sorted(
            daily_data.values(),
            key=lambda x: x['date']
        )
        
        sorted_class_data = sorted(
            class_data.values(),
            key=lambda x: (x['class_level'].name, x['stream'].stream_letter if x['stream'] else '')
        )
        
        sorted_student_data = sorted(
            student_data.values(),
            key=lambda x: (x['student'].class_level.name if x['student'].class_level else '', 
                          x['student'].last_name, x['student'].first_name)
        )
        
        # Calculate monthly trends (daily attendance rates)
        daily_trends = []
        for day_data in sorted_daily_data:
            daily_trends.append({
                'date': day_data['date'],
                'day_name': day_data['day_name'],
                'sessions': day_data['sessions'],
                'attendance_rate': day_data['attendance_rate'],
                'present': day_data['present'],
                'total': day_data['students']
            })
        
        # Calculate weekly summary
        weekly_summary = self.calculate_weekly_summary(sorted_daily_data, start_date, end_date)
        
        # Prepare context
        context.update({
            'month': month,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'month_name': start_date.strftime('%B %Y'),
            'daily_data': sorted_daily_data,
            'class_data': sorted_class_data,
            'student_data': sorted_student_data,
            'total_stats': total_stats,
            'daily_trends': daily_trends,
            'weekly_summary': weekly_summary,
            'class_levels': ClassLevel.objects.all(),
            'filter_class': class_filter,
            'filter_stream': stream_filter,
            'filter_type': attendance_type,
            'filter_view': view_mode,
            'attendance_types': [
                ('ALL', 'All Types'),
                ('CLASS', 'Class Wise'),
                ('SUBJECT', 'Subject Wise')
            ],
            'view_modes': [
                ('summary', 'Summary View'),
                ('detailed', 'Detailed View'),
                ('both', 'Both Views')
            ],
            'has_data': len(attendance_sessions) > 0,
            'total_days_in_month': (end_date - start_date).days + 1,
            'days_with_data': len(daily_data),
        })
        
        # Get streams for selected class
        if class_filter:
            context['streams'] = StreamClass.objects.filter(
                class_level_id=class_filter, 
                is_active=True
            )
        else:
            context['streams'] = StreamClass.objects.none()
        
        return context
    
    def calculate_weekly_summary(self, daily_data, start_date, end_date):
        """Calculate weekly attendance summary"""
        weekly_summary = []
        
        # Group days by week
        current_date = start_date
        week_data = []
        week_start = start_date
        
        for day_data in daily_data:
            # If this day is more than 7 days from week_start or it's a Monday, start new week
            if (day_data['date'] - week_start).days >= 7 or day_data['date'].weekday() == 0:
                if week_data:
                    weekly_summary.append(self.calculate_week_stats(week_data, week_start))
                week_data = []
                week_start = day_data['date']
            
            week_data.append(day_data)
        
        # Add the last week
        if week_data:
            weekly_summary.append(self.calculate_week_stats(week_data, week_start))
        
        return weekly_summary
    
    def calculate_week_stats(self, week_data, week_start):
        """Calculate statistics for a week"""
        total_sessions = sum(day['sessions'] for day in week_data)
        total_students = sum(day['students'] for day in week_data)
        total_present = sum(day['present'] for day in week_data)
        total_absent = sum(day['absent'] for day in week_data)
        total_late = sum(day['late'] for day in week_data)
        total_excused = sum(day['excused'] for day in week_data)
        
        attendance_rate = 0
        if total_students > 0:
            attendance_rate = round((total_present / total_students) * 100, 2)
        
        week_end = week_data[-1]['date'] if week_data else week_start
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'week_number': week_start.isocalendar()[1],
            'days': len(week_data),
            'sessions': total_sessions,
            'students': total_students,
            'present': total_present,
            'absent': total_absent,
            'late': total_late,
            'excused': total_excused,
            'attendance_rate': attendance_rate
        }
    

# attendance/views.py - Add this class

class ExportMonthlyAttendancePDFView(AdminRequiredMixin, View):
    """Export monthly attendance report as PDF"""
    
    def get(self, request):
        try:
            # Get filter parameters from request
            month = request.GET.get('month', timezone.now().month)
            year = request.GET.get('year', timezone.now().year)
            class_filter = request.GET.get('class_level', '')
            stream_filter = request.GET.get('stream', '')
            attendance_type = request.GET.get('attendance_type', 'ALL')
            view_mode = request.GET.get('view', 'summary')
            
            # Convert month and year to integers
            try:
                month = int(month)
                year = int(year)
            except (ValueError, TypeError):
                month = timezone.now().month
                year = timezone.now().year
            
            # Calculate date range for the month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Get attendance sessions for the month
            attendance_sessions = AttendanceSession.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).select_related(
                'class_level', 'stream', 'subject'
            ).order_by('date', 'class_level__name', 'stream__stream_letter')
            
            # Apply additional filters
            if class_filter:
                attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
            if stream_filter:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Check if data exists
            if not attendance_sessions.exists():
                raise Exception(f"No attendance data found for {start_date.strftime('%B %Y')} with selected filters")
            
            # Prepare data structures (similar to MonthlyAttendanceReportView)
            daily_data = {}
            class_data = {}
            student_data = {}
            
            total_stats = {
                'days': 0,
                'sessions': 0,
                'students': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'excused': 0,
                'attendance_rate': 0
            }
            
            # Process each attendance session
            for session in attendance_sessions:
                date_str = session.date.strftime('%Y-%m-%d')
                class_key = f"{session.class_level.name}_{session.stream.stream_letter if session.stream else 'ALL'}"
                
                # Initialize data structures
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': session.date,
                        'day_name': session.date.strftime('%A'),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                if class_key not in class_data:
                    class_data[class_key] = {
                        'class_level': session.class_level,
                        'stream': session.stream,
                        'days': set(),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                # Get attendance records
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                )
                
                # Calculate session statistics
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                for key in ['total', 'present', 'absent', 'late', 'excused']:
                    session_stats[key] = session_stats[key] or 0
                
                # Update statistics
                daily_data[date_str]['sessions'] += 1
                daily_data[date_str]['students'] += session_stats['total']
                daily_data[date_str]['present'] += session_stats['present']
                daily_data[date_str]['absent'] += session_stats['absent']
                daily_data[date_str]['late'] += session_stats['late']
                daily_data[date_str]['excused'] += session_stats['excused']
                
                class_data[class_key]['days'].add(session.date)
                class_data[class_key]['sessions'] += 1
                class_data[class_key]['students'] += session_stats['total']
                class_data[class_key]['present'] += session_stats['present']
                class_data[class_key]['absent'] += session_stats['absent']
                class_data[class_key]['late'] += session_stats['late']
                class_data[class_key]['excused'] += session_stats['excused']
                
                total_stats['sessions'] += 1
                total_stats['students'] += session_stats['total']
                total_stats['present'] += session_stats['present']
                total_stats['absent'] += session_stats['absent']
                total_stats['late'] += session_stats['late']
                total_stats['excused'] += session_stats['excused']
                
                # Collect student data for detailed view
                if view_mode in ['detailed', 'both']:
                    for attendance in student_attendances.select_related('student'):
                        student_id = attendance.student_id
                        if student_id not in student_data:
                            student_data[student_id] = {
                                'student': attendance.student,
                                'days': set(),
                                'sessions': 0,
                                'present': 0,
                                'absent': 0,
                                'late': 0,
                                'excused': 0,
                                'attendance_rate': 0
                            }
                        
                        student = student_data[student_id]
                        student['days'].add(session.date)
                        student['sessions'] += 1
                        
                        if attendance.status == 'P':
                            student['present'] += 1
                        elif attendance.status == 'A':
                            student['absent'] += 1
                        elif attendance.status == 'L':
                            student['late'] += 1
                        elif attendance.status == 'E':
                            student['excused'] += 1
            
            # Calculate rates
            total_stats['days'] = len(daily_data)
            if total_stats['students'] > 0:
                total_stats['attendance_rate'] = round(
                    (total_stats['present'] / total_stats['students']) * 100, 2
                )
            
            for date_str, day_data in daily_data.items():
                if day_data['students'] > 0:
                    day_data['attendance_rate'] = round(
                        (day_data['present'] / day_data['students']) * 100, 2
                    )
            
            for class_key, cdata in class_data.items():
                cdata['days'] = len(cdata['days'])
                if cdata['students'] > 0:
                    cdata['attendance_rate'] = round(
                        (cdata['present'] / cdata['students']) * 100, 2
                    )
            
            for student_id, sdata in student_data.items():
                sdata['days'] = len(sdata['days'])
                if sdata['sessions'] > 0:
                    sdata['attendance_rate'] = round(
                        (sdata['present'] / sdata['sessions']) * 100, 2
                    )
            
            # Sort data
            sorted_daily_data = sorted(
                daily_data.values(),
                key=lambda x: x['date']
            )
            
            sorted_class_data = sorted(
                class_data.values(),
                key=lambda x: (x['class_level'].name, x['stream'].stream_letter if x['stream'] else '')
            )
            
            sorted_student_data = sorted(
                student_data.values(),
                key=lambda x: (x['student'].class_level.name if x['student'].class_level else '', 
                              x['student'].last_name, x['student'].first_name)
            )
            
            # Calculate weekly summary
            weekly_summary = []
            if sorted_daily_data:
                week_data = []
                week_start = sorted_daily_data[0]['date']
                
                for day_data in sorted_daily_data:
                    if (day_data['date'] - week_start).days >= 7 or day_data['date'].weekday() == 0:
                        if week_data:
                            weekly_summary.append(self.calculate_week_stats(week_data, week_start))
                        week_data = []
                        week_start = day_data['date']
                    week_data.append(day_data)
                
                if week_data:
                    weekly_summary.append(self.calculate_week_stats(week_data, week_start))
            
            # Get school information
            from django.conf import settings
            school_name = getattr(settings, 'SCHOOL_NAME', 'Your School Name')
            school_address = getattr(settings, 'SCHOOL_ADDRESS', 'Your School Address')
            
            # Prepare context
            context = {
                'month': month,
                'year': year,
                'start_date': start_date,
                'end_date': end_date,
                'month_name': start_date.strftime('%B %Y'),
                'daily_data': sorted_daily_data,
                'class_data': sorted_class_data,
                'student_data': sorted_student_data,
                'total_stats': total_stats,
                'weekly_summary': weekly_summary,
                'school_name': school_name,
                'school_address': school_address,
                'generation_date': timezone.now().strftime('%B %d, %Y %I:%M %p'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'filter_class_name': '',
                'filter_stream_name': '',
                'filter_type_name': '',
                'filter_view': view_mode,
                'total_days_in_month': (end_date - start_date).days + 1,
                'days_with_data': len(daily_data),
                'has_data': True,
            }
            
            # Add filter information
            if class_filter:
                try:
                    class_obj = ClassLevel.objects.get(id=class_filter)
                    context['filter_class_name'] = class_obj.name
                except ClassLevel.DoesNotExist:
                    pass
            
            if stream_filter:
                try:
                    stream_obj = StreamClass.objects.get(id=stream_filter)
                    context['filter_stream_name'] = stream_obj.stream_letter
                except StreamClass.DoesNotExist:
                    pass
            
            if attendance_type != 'ALL':
                type_display = dict(AttendanceSession.ATTENDANCE_TYPE_CHOICES).get(attendance_type, attendance_type)
                context['filter_type_name'] = type_display
            
            # Render the HTML template
            html_string = render_to_string('admin/attendance/reports/monthly_report_pdf.html', context)
            
            # Configure fonts for PDF generation
            font_config = FontConfiguration()
            
            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = html.write_pdf(font_config=font_config)
            
            # Create HTTP response
            response = HttpResponse(pdf_file, content_type='application/pdf')
            
            # Generate filename
            filename = f"monthly_attendance_{start_date.strftime('%B_%Y')}"
            if context['filter_class_name']:
                filename += f"_{context['filter_class_name'].replace(' ', '_')}"
            if context['filter_stream_name']:
                filename += f"_Stream_{context['filter_stream_name']}"
            if view_mode != 'summary':
                filename += f"_{view_mode}_view"
            filename += ".pdf"
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error generating PDF: {e}")
            print(traceback.format_exc())
            
            messages.error(request, f"Failed to generate PDF: {str(e)}")
            return redirect('attendance_report_monthly')
    
    def calculate_week_stats(self, week_data, week_start):
        """Calculate statistics for a week"""
        total_sessions = sum(day['sessions'] for day in week_data)
        total_students = sum(day['students'] for day in week_data)
        total_present = sum(day['present'] for day in week_data)
        total_absent = sum(day['absent'] for day in week_data)
        total_late = sum(day['late'] for day in week_data)
        total_excused = sum(day['excused'] for day in week_data)
        
        attendance_rate = 0
        if total_students > 0:
            attendance_rate = round((total_present / total_students) * 100, 2)
        
        week_end = week_data[-1]['date'] if week_data else week_start
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'week_number': week_start.isocalendar()[1],
            'days': len(week_data),
            'sessions': total_sessions,
            'students': total_students,
            'present': total_present,
            'absent': total_absent,
            'late': total_late,
            'excused': total_excused,
            'attendance_rate': attendance_rate
        }


# attendance/views.py - Add these views at the appropriate location

class WeeklyAttendancePDFView(AdminRequiredMixin, View):
    """Generate PDF report for weekly attendance"""
    
    def get(self, request):
        try:
            # Get filter parameters from request
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            class_filter = request.GET.get('class_level', '')
            stream_filter = request.GET.get('stream', '')
            attendance_type = request.GET.get('attendance_type', 'ALL')
            
            # Validate required parameters
            if not start_date or not end_date:
                raise Exception("Start date and end date are required")
            
            # Parse dates
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Get attendance sessions for the week
            attendance_sessions = AttendanceSession.objects.filter(
                date__gte=start_date_obj,
                date__lte=end_date_obj
            ).select_related(
                'class_level', 'stream', 'subject'
            ).order_by('date', 'class_level__name', 'stream__stream_letter')
            
            # Apply additional filters
            if class_filter:
                attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
            if stream_filter:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Check if data exists
            if not attendance_sessions.exists():
                raise Exception(f"No attendance data found for period {start_date} to {end_date}")
            
            # Prepare data structures
            daily_data = {}
            class_data = {}
            student_data = {}
            
            total_stats = {
                'days': 0,
                'sessions': 0,
                'students': 0,
                'present': 0,
                'absent': 0,
                'late': 0,
                'excused': 0,
                'attendance_rate': 0
            }
            
            # Process each attendance session
            for session in attendance_sessions:
                date_str = session.date.strftime('%Y-%m-%d')
                class_key = f"{session.class_level.name}_{session.stream.stream_letter if session.stream else 'ALL'}"
                
                # Initialize daily data if not exists
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': session.date,
                        'day_name': session.date.strftime('%A'),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                # Initialize class data if not exists
                if class_key not in class_data:
                    class_data[class_key] = {
                        'class_level': session.class_level,
                        'stream': session.stream,
                        'days': set(),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                # Get attendance records for this session
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                )
                
                # Calculate session statistics
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                for key in ['total', 'present', 'absent', 'late', 'excused']:
                    session_stats[key] = session_stats[key] or 0
                
                # Update daily statistics
                daily_data[date_str]['sessions'] += 1
                daily_data[date_str]['students'] += session_stats['total']
                daily_data[date_str]['present'] += session_stats['present']
                daily_data[date_str]['absent'] += session_stats['absent']
                daily_data[date_str]['late'] += session_stats['late']
                daily_data[date_str]['excused'] += session_stats['excused']
                
                # Update class statistics
                class_data[class_key]['days'].add(session.date)
                class_data[class_key]['sessions'] += 1
                class_data[class_key]['students'] += session_stats['total']
                class_data[class_key]['present'] += session_stats['present']
                class_data[class_key]['absent'] += session_stats['absent']
                class_data[class_key]['late'] += session_stats['late']
                class_data[class_key]['excused'] += session_stats['excused']
                
                # Update total statistics
                total_stats['sessions'] += 1
                total_stats['students'] += session_stats['total']
                total_stats['present'] += session_stats['present']
                total_stats['absent'] += session_stats['absent']
                total_stats['late'] += session_stats['late']
                total_stats['excused'] += session_stats['excused']
                
                # Track individual student attendance
                for attendance in student_attendances.select_related('student'):
                    student_id = attendance.student_id
                    if student_id not in student_data:
                        student_data[student_id] = {
                            'student': attendance.student,
                            'days': set(),
                            'sessions': 0,
                            'present': 0,
                            'absent': 0,
                            'late': 0,
                            'excused': 0,
                            'attendance_rate': 0
                        }
                    
                    student = student_data[student_id]
                    student['days'].add(session.date)
                    student['sessions'] += 1
                    
                    if attendance.status == 'P':
                        student['present'] += 1
                    elif attendance.status == 'A':
                        student['absent'] += 1
                    elif attendance.status == 'L':
                        student['late'] += 1
                    elif attendance.status == 'E':
                        student['excused'] += 1
            
            # Calculate attendance rates
            total_stats['days'] = len(daily_data)
            if total_stats['students'] > 0:
                total_stats['attendance_rate'] = round(
                    (total_stats['present'] / total_stats['students']) * 100, 2
                )
            
            # Calculate daily attendance rates
            for date_str, day_data in daily_data.items():
                if day_data['students'] > 0:
                    day_data['attendance_rate'] = round(
                        (day_data['present'] / day_data['students']) * 100, 2
                    )
            
            # Calculate class attendance rates and convert days set to count
            for class_key, cdata in class_data.items():
                cdata['days'] = len(cdata['days'])
                if cdata['students'] > 0:
                    cdata['attendance_rate'] = round(
                        (cdata['present'] / cdata['students']) * 100, 2
                    )
            
            # Calculate student attendance rates
            for student_id, sdata in student_data.items():
                sdata['days'] = len(sdata['days'])
                if sdata['sessions'] > 0:
                    sdata['attendance_rate'] = round(
                        (sdata['present'] / sdata['sessions']) * 100, 2
                    )
            
            # Sort data
            sorted_daily_data = sorted(
                daily_data.values(),
                key=lambda x: x['date']
            )
            
            sorted_class_data = sorted(
                class_data.values(),
                key=lambda x: (x['class_level'].name, x['stream'].stream_letter if x['stream'] else '')
            )
            
            sorted_student_data = sorted(
                student_data.values(),
                key=lambda x: (x['student'].class_level.name if x['student'].class_level else '', 
                              x['student'].last_name, x['student'].first_name)
            )[:50]  # Limit to top 50 students
            
            # Get school information
            from django.conf import settings
            school_name = getattr(settings, 'SCHOOL_NAME', 'Your School Name')
            school_address = getattr(settings, 'SCHOOL_ADDRESS', 'Your School Address')
            
            # Prepare context
            context = {
                'start_date': start_date,
                'end_date': end_date,
                'start_date_obj': start_date_obj,
                'end_date_obj': end_date_obj,
                'daily_data': sorted_daily_data,
                'class_data': sorted_class_data,
                'student_data': sorted_student_data,
                'total_stats': total_stats,
                'school_name': school_name,
                'school_address': school_address,
                'generation_date': timezone.now().strftime('%B %d, %Y %I:%M %p'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'filter_class_name': '',
                'filter_stream_name': '',
                'filter_type_name': '',
                'has_data': True,
                'week_duration': (end_date_obj - start_date_obj).days + 1,
                'total_classes': len(class_data),
                'total_students': len(student_data),
            }
            
            # Add filter information if filters were applied
            if class_filter:
                try:
                    class_obj = ClassLevel.objects.get(id=class_filter)
                    context['filter_class_name'] = class_obj.name
                except ClassLevel.DoesNotExist:
                    pass
            
            if stream_filter:
                try:
                    stream_obj = StreamClass.objects.get(id=stream_filter)
                    context['filter_stream_name'] = stream_obj.stream_letter
                except StreamClass.DoesNotExist:
                    pass
            
            if attendance_type != 'ALL':
                type_display = dict(AttendanceSession.ATTENDANCE_TYPE_CHOICES).get(attendance_type, attendance_type)
                context['filter_type_name'] = type_display
            
            # Render the HTML template
            html_string = render_to_string('admin/attendance/reports/weekly_report_pdf.html', context)
            
            # Configure fonts for PDF generation
            font_config = FontConfiguration()
            
            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = html.write_pdf(font_config=font_config)
            
            # Create HTTP response
            response = HttpResponse(pdf_file, content_type='application/pdf')
            
            # Generate filename
            filename = f"weekly_attendance_{start_date}_to_{end_date}"
            if context['filter_class_name']:
                filename += f"_{context['filter_class_name'].replace(' ', '_')}"
            if context['filter_stream_name']:
                filename += f"_Stream_{context['filter_stream_name']}"
            filename += ".pdf"
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error generating weekly PDF: {e}")
            print(traceback.format_exc())
            
            # Store error in session and redirect back
            messages.error(request, f"Failed to generate PDF: {str(e)}")
            
            # Redirect to monthly report page with error message
            return redirect('attendance_report_monthly')


class ClassMonthlyAttendancePDFView(AdminRequiredMixin, View):
    """Generate PDF report for class monthly attendance"""
    
    def get(self, request):
        try:
            # Get filter parameters from request
            class_filter = request.GET.get('class_level')
            stream_filter = request.GET.get('stream')
            month = request.GET.get('month', timezone.now().month)
            year = request.GET.get('year', timezone.now().year)
            attendance_type = request.GET.get('attendance_type', 'ALL')
            
            # Validate required parameters
            if not class_filter:
                raise Exception("Class level is required")
            
            # Convert month and year to integers
            try:
                month = int(month)
                year = int(year)
            except (ValueError, TypeError):
                month = timezone.now().month
                year = timezone.now().year
            
            # Calculate date range for the month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # Get class and stream information
            class_level = get_object_or_404(ClassLevel, id=class_filter)
            stream = None
            if stream_filter:
                stream = get_object_or_404(StreamClass, id=stream_filter)
            
            # Get attendance sessions for the class and month
            attendance_sessions = AttendanceSession.objects.filter(
                class_level_id=class_filter,
                date__gte=start_date,
                date__lte=end_date
            ).select_related('subject')
            
            if stream_filter:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
            
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Check if data exists
            if not attendance_sessions.exists():
                raise Exception(f"No attendance data found for {class_level.name} in {start_date.strftime('%B %Y')}")
            
            # Get students in this class/stream
            students = Student.objects.filter(
                class_level_id=class_filter,
                is_active=True
            )
            
            if stream_filter:
                students = students.filter(stream_class_id=stream_filter)
            
            # Prepare data structures
            daily_data = {}
            student_attendance_data = {}
            subject_data = {}
            
            # Initialize student data
            for student in students:
                student_attendance_data[student.id] = {
                    'student': student,
                    'days': set(),
                    'sessions': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'attendance_rate': 0
                }
            
            # Process each session
            for session in attendance_sessions:
                date_str = session.date.strftime('%Y-%m-%d')
                
                # Initialize daily data
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': session.date,
                        'day_name': session.date.strftime('%A'),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                # Initialize subject data
                subject_name = session.subject.name if session.subject else 'Class Attendance'
                if subject_name not in subject_data:
                    subject_data[subject_name] = {
                        'name': subject_name,
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'attendance_rate': 0
                    }
                
                # Get attendance for this session
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                ).select_related('student')
                
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                for key in ['total', 'present', 'absent', 'late', 'excused']:
                    session_stats[key] = session_stats[key] or 0
                
                # Update daily data
                daily_data[date_str]['sessions'] += 1
                daily_data[date_str]['students'] += session_stats['total']
                daily_data[date_str]['present'] += session_stats['present']
                daily_data[date_str]['absent'] += session_stats['absent']
                daily_data[date_str]['late'] += session_stats['late']
                daily_data[date_str]['excused'] += session_stats['excused']
                
                # Update subject data
                subject_data[subject_name]['sessions'] += 1
                subject_data[subject_name]['students'] += session_stats['total']
                subject_data[subject_name]['present'] += session_stats['present']
                subject_data[subject_name]['absent'] += session_stats['absent']
                subject_data[subject_name]['late'] += session_stats['late']
                subject_data[subject_name]['excused'] += session_stats['excused']
                
                # Update student data
                for attendance in student_attendances:
                    student_id = attendance.student_id
                    if student_id in student_attendance_data:
                        student_data = student_attendance_data[student_id]
                        student_data['days'].add(session.date)
                        student_data['sessions'] += 1
                        
                        if attendance.status == 'P':
                            student_data['present'] += 1
                        elif attendance.status == 'A':
                            student_data['absent'] += 1
                        elif attendance.status == 'L':
                            student_data['late'] += 1
                        elif attendance.status == 'E':
                            student_data['excused'] += 1
            
            # Calculate rates
            for date_str, data in daily_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
            
            for subject_name, data in subject_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
            
            for student_id, data in student_attendance_data.items():
                data['days'] = len(data['days'])
                if data['sessions'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['sessions']) * 100, 2)
            
            # Calculate month totals
            month_totals = {
                'days': len(daily_data),
                'sessions': sum(d['sessions'] for d in daily_data.values()),
                'students': sum(d['students'] for d in daily_data.values()),
                'present': sum(d['present'] for d in daily_data.values()),
                'absent': sum(d['absent'] for d in daily_data.values()),
                'late': sum(d['late'] for d in daily_data.values()),
                'excused': sum(d['excused'] for d in daily_data.values()),
                'attendance_rate': 0
            }
            
            if month_totals['students'] > 0:
                month_totals['attendance_rate'] = round(
                    (month_totals['present'] / month_totals['students']) * 100, 2
                )
            
            # Sort data
            sorted_daily_data = sorted(
                daily_data.values(),
                key=lambda x: x['date']
            )
            
            sorted_subject_data = sorted(
                subject_data.values(),
                key=lambda x: x['name']
            )
            
            sorted_student_data = sorted(
                student_attendance_data.values(),
                key=lambda x: (x['student'].last_name, x['student'].first_name)
            )
            
            # Get school information
            from django.conf import settings
            school_name = getattr(settings, 'SCHOOL_NAME', 'Your School Name')
            school_address = getattr(settings, 'SCHOOL_ADDRESS', 'Your School Address')
            
            # Prepare context
            context = {
                'class_level': class_level,
                'stream': stream,
                'month': month,
                'year': year,
                'start_date': start_date,
                'end_date': end_date,
                'month_name': start_date.strftime('%B %Y'),
                'daily_data': sorted_daily_data,
                'subject_data': sorted_subject_data,
                'student_data': sorted_student_data,
                'month_totals': month_totals,
                'school_name': school_name,
                'school_address': school_address,
                'generation_date': timezone.now().strftime('%B %d, %Y %I:%M %p'),
                'generated_by': request.user.get_full_name() or request.user.username,
                'total_students': students.count(),
                'total_days': len(daily_data),
                'total_sessions': attendance_sessions.count(),
                'has_data': True,
            }
            
            # Add attendance type filter information
            if attendance_type != 'ALL':
                type_display = dict(AttendanceSession.ATTENDANCE_TYPE_CHOICES).get(attendance_type, attendance_type)
                context['filter_type_name'] = type_display
            else:
                context['filter_type_name'] = 'All Types'
            
            # Render the HTML template
            html_string = render_to_string('admin/attendance/reports/class_monthly_report_pdf.html', context)
            
            # Configure fonts for PDF generation
            font_config = FontConfiguration()
            
            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = html.write_pdf(font_config=font_config)
            
            # Create HTTP response
            response = HttpResponse(pdf_file, content_type='application/pdf')
            
            # Generate filename
            filename = f"class_attendance_{class_level.name.replace(' ', '_')}"
            if stream:
                filename += f"_Stream_{stream.stream_letter}"
            filename += f"_{start_date.strftime('%B_%Y')}.pdf"
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error generating class monthly PDF: {e}")
            print(traceback.format_exc())
            
            # Store error in session and redirect back
            messages.error(request, f"Failed to generate PDF: {str(e)}")
            
            # Redirect to monthly report page with error message
            return redirect('attendance_report_monthly')



class GetWeekAttendanceDetailsAPI(AdminRequiredMixin, View):
    """API to get detailed week attendance data"""
    
    def get(self, request):
        try:
            start_date_str = request.GET.get('start_date')
            end_date_str = request.GET.get('end_date')
            class_filter = request.GET.get('class_level', '')
            stream_filter = request.GET.get('stream', '')
            attendance_type = request.GET.get('attendance_type', 'ALL')
            
            if not start_date_str or not end_date_str:
                return JsonResponse({
                    'success': False,
                    'message': 'Start date and end date are required'
                }, status=400)
            
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Get attendance sessions for the week
            attendance_sessions = AttendanceSession.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).select_related(
                'class_level', 'stream', 'subject'
            ).order_by('date', 'class_level__name')
            
            # Apply filters
            if class_filter:
                attendance_sessions = attendance_sessions.filter(class_level_id=class_filter)
            if stream_filter:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_filter)
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Prepare daily breakdown
            daily_data = {}
            class_data = {}
            student_data = {}
            
            for session in attendance_sessions:
                date_str = session.date.strftime('%Y-%m-%d')
                class_key = f"{session.class_level.name}_{session.stream.stream_letter if session.stream else 'ALL'}"
                
                # Initialize daily data
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': session.date.strftime('%Y-%m-%d'),
                        'day_name': session.date.strftime('%A'),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                # Initialize class data
                if class_key not in class_data:
                    class_data[class_key] = {
                        'class_level': session.class_level.name,
                        'stream': session.stream.stream_letter if session.stream else 'All',
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                # Get attendance for this session
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                ).select_related('student')
                
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                # Update daily data
                daily_data[date_str]['sessions'] += 1
                daily_data[date_str]['students'] += session_stats['total'] or 0
                daily_data[date_str]['present'] += session_stats['present'] or 0
                daily_data[date_str]['absent'] += session_stats['absent'] or 0
                daily_data[date_str]['late'] += session_stats['late'] or 0
                daily_data[date_str]['excused'] += session_stats['excused'] or 0
                
                # Update class data
                class_data[class_key]['sessions'] += 1
                class_data[class_key]['students'] += session_stats['total'] or 0
                class_data[class_key]['present'] += session_stats['present'] or 0
                class_data[class_key]['absent'] += session_stats['absent'] or 0
                class_data[class_key]['late'] += session_stats['late'] or 0
                class_data[class_key]['excused'] += session_stats['excused'] or 0
                
                # Collect student data
                for attendance in student_attendances:
                    student_id = attendance.student_id
                    if student_id not in student_data:
                        student_data[student_id] = {
                            'student_id': student_id,
                            'name': attendance.student.full_name,
                            'admission_number': attendance.student.registration_number or '',
                            'class': attendance.student.class_level.name if attendance.student.class_level else '',
                            'sessions': 0,
                            'present': 0,
                            'absent': 0,
                            'late': 0,
                            'excused': 0
                        }
                    
                    student = student_data[student_id]
                    student['sessions'] += 1
                    
                    if attendance.status == 'P':
                        student['present'] += 1
                    elif attendance.status == 'A':
                        student['absent'] += 1
                    elif attendance.status == 'L':
                        student['late'] += 1
                    elif attendance.status == 'E':
                        student['excused'] += 1
            
            # Calculate rates
            for date_str, data in daily_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
                else:
                    data['attendance_rate'] = 0
            
            for class_key, data in class_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
                else:
                    data['attendance_rate'] = 0
            
            for student_id, data in student_data.items():
                if data['sessions'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['sessions']) * 100, 2)
                else:
                    data['attendance_rate'] = 0
            
            # Convert to lists for JSON response
            daily_list = list(daily_data.values())
            class_list = list(class_data.values())
            student_list = list(student_data.values())
            
            # Calculate week totals
            week_totals = {
                'days': len(daily_list),
                'sessions': sum(d['sessions'] for d in daily_list),
                'students': sum(d['students'] for d in daily_list),
                'present': sum(d['present'] for d in daily_list),
                'absent': sum(d['absent'] for d in daily_list),
                'late': sum(d['late'] for d in daily_list),
                'excused': sum(d['excused'] for d in daily_list),
                'attendance_rate': 0
            }
            
            if week_totals['students'] > 0:
                week_totals['attendance_rate'] = round((week_totals['present'] / week_totals['students']) * 100, 2)
            
            return JsonResponse({
                'success': True,
                'week': {
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'totals': week_totals
                },
                'daily_breakdown': daily_list,
                'class_breakdown': class_list,
                'student_breakdown': student_list[:50],  # Limit to top 50 students
                'total_students': len(student_list)
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=500)


class GetClassAttendanceDetailsAPI(AdminRequiredMixin, View):
    """API to get detailed class attendance data for a month"""
    
    def get(self, request):
        try:
            class_id = request.GET.get('class_id')
            stream_id = request.GET.get('stream_id')
            month = request.GET.get('month', datetime.now().month)
            year = request.GET.get('year', datetime.now().year)
            attendance_type = request.GET.get('attendance_type', 'ALL')
            
            if not class_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Class ID is required'
                }, status=400)
            
            # Calculate date range for the month
            start_date = datetime(int(year), int(month), 1).date()
            if int(month) == 12:
                end_date = datetime(int(year) + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(int(year), int(month) + 1, 1).date() - timedelta(days=1)
            
            # Get class information
            class_level = get_object_or_404(ClassLevel, id=class_id)
            stream = None
            if stream_id:
                stream = get_object_or_404(StreamClass, id=stream_id)
            
            # Get attendance sessions for this class
            attendance_sessions = AttendanceSession.objects.filter(
                class_level_id=class_id,
                date__gte=start_date,
                date__lte=end_date
            ).select_related('subject')
            
            if stream_id:
                attendance_sessions = attendance_sessions.filter(stream_id=stream_id)
            
            if attendance_type and attendance_type != 'ALL':
                attendance_sessions = attendance_sessions.filter(attendance_type=attendance_type)
            
            # Get students in this class/stream
            students = Student.objects.filter(
                class_level_id=class_id,
                is_active=True
            )
            
            if stream_id:
                students = students.filter(stream_class_id=stream_id)
            
            # Prepare daily breakdown
            daily_data = {}
            student_attendance_data = {}
            subject_data = {}
            
            # Initialize student data
            for student in students:
                student_attendance_data[student.id] = {
                    'student_id': student.id,
                    'name': student.full_name,
                    'admission_number': student.registration_number or '',
                    'days': set(),
                    'sessions': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'attendance_rate': 0
                }
            
            # Process each session
            for session in attendance_sessions:
                date_str = session.date.strftime('%Y-%m-%d')
                
                # Initialize daily data
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': session.date.strftime('%Y-%m-%d'),
                        'day_name': session.date.strftime('%A'),
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                # Initialize subject data
                subject_name = session.subject.name if session.subject else 'Class Attendance'
                if subject_name not in subject_data:
                    subject_data[subject_name] = {
                        'name': subject_name,
                        'sessions': 0,
                        'students': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                # Get attendance for this session
                student_attendances = StudentAttendance.objects.filter(
                    attendance_session=session
                ).select_related('student')
                
                session_stats = student_attendances.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                # Update daily data
                daily_data[date_str]['sessions'] += 1
                daily_data[date_str]['students'] += session_stats['total'] or 0
                daily_data[date_str]['present'] += session_stats['present'] or 0
                daily_data[date_str]['absent'] += session_stats['absent'] or 0
                daily_data[date_str]['late'] += session_stats['late'] or 0
                daily_data[date_str]['excused'] += session_stats['excused'] or 0
                
                # Update subject data
                subject_data[subject_name]['sessions'] += 1
                subject_data[subject_name]['students'] += session_stats['total'] or 0
                subject_data[subject_name]['present'] += session_stats['present'] or 0
                subject_data[subject_name]['absent'] += session_stats['absent'] or 0
                subject_data[subject_name]['late'] += session_stats['late'] or 0
                subject_data[subject_name]['excused'] += session_stats['excused'] or 0
                
                # Update student data
                for attendance in student_attendances:
                    student_id = attendance.student_id
                    if student_id in student_attendance_data:
                        student_data = student_attendance_data[student_id]
                        student_data['days'].add(session.date)
                        student_data['sessions'] += 1
                        
                        if attendance.status == 'P':
                            student_data['present'] += 1
                        elif attendance.status == 'A':
                            student_data['absent'] += 1
                        elif attendance.status == 'L':
                            student_data['late'] += 1
                        elif attendance.status == 'E':
                            student_data['excused'] += 1
            
            # Calculate rates
            for date_str, data in daily_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
                else:
                    data['attendance_rate'] = 0
            
            for subject_name, data in subject_data.items():
                if data['students'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['students']) * 100, 2)
                else:
                    data['attendance_rate'] = 0
            
            for student_id, data in student_attendance_data.items():
                data['days'] = len(data['days'])
                if data['sessions'] > 0:
                    data['attendance_rate'] = round((data['present'] / data['sessions']) * 100, 2)
            
            # Calculate month totals
            month_totals = {
                'days': len(daily_data),
                'sessions': sum(d['sessions'] for d in daily_data.values()),
                'students': sum(d['students'] for d in daily_data.values()),
                'present': sum(d['present'] for d in daily_data.values()),
                'absent': sum(d['absent'] for d in daily_data.values()),
                'late': sum(d['late'] for d in daily_data.values()),
                'excused': sum(d['excused'] for d in daily_data.values()),
                'attendance_rate': 0
            }
            
            if month_totals['students'] > 0:
                month_totals['attendance_rate'] = round((month_totals['present'] / month_totals['students']) * 100, 2)
            
            # Convert sets to lists for JSON
            for student_id, data in student_attendance_data.items():
                if 'days' in data and isinstance(data['days'], set):
                    data['days'] = list(data['days'])
            
            return JsonResponse({
                'success': True,
                'class_info': {
                    'class_name': class_level.name,
                    'stream_name': stream.stream_letter if stream else 'All Streams',
                    'month': start_date.strftime('%B %Y'),
                    'total_students': students.count()
                },
                'month_totals': month_totals,
                'daily_breakdown': list(daily_data.values()),
                'subject_breakdown': list(subject_data.values()),
                'student_breakdown': list(student_attendance_data.values()),
                'total_sessions': attendance_sessions.count()
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=500)
        




class ClassAttendanceReportView(AdminRequiredMixin, TemplateView):
    template_name = 'attendance/reports/class.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        
        class_level = get_object_or_404(ClassLevel, id=class_id)
        
        # Get date range from query params
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).date()
        if not end_date:
            end_date = datetime.now().date()
        
        # Get attendance sessions for this class
        attendance_sessions = AttendanceSession.objects.filter(
            class_level=class_level,
            date__gte=start_date,
            date__lte=end_date
        )
        
        # Get students in this class
        students = Student.objects.filter(
            current_class=class_level,
            is_active=True
        )
        
        # Calculate attendance for each student
        student_attendance = []
        for student in students:
            student_records = StudentAttendance.objects.filter(
                student=student,
                attendance_session__in=attendance_sessions
            )
            
            student_stats = student_records.aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='P')),
                absent=Count('id', filter=Q(status='A')),
                late=Count('id', filter=Q(status='L')),
                excused=Count('id', filter=Q(status='E'))
            )
            
            attendance_rate = 0
            if student_stats['total'] > 0:
                attendance_rate = round(
                    (student_stats['present'] / student_stats['total']) * 100, 2
                )
            
            student_attendance.append({
                'student': student,
                'stats': student_stats,
                'attendance_rate': attendance_rate
            })
        
        context['class_level'] = class_level
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['student_attendance'] = student_attendance
        context['total_sessions'] = attendance_sessions.count()
        
        return context




# Edit the EditAttendanceSessionView and add proper API endpoints
class EditAttendanceSessionView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/attendance/edit_session.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        session_id = self.kwargs.get('session_id')
        
        # Get the session to check its type
        try:
            session = AttendanceSession.objects.select_related(
                'class_level', 'stream', 'subject'
            ).get(id=session_id)
            
            # Add complete session data to context
            context['session_data'] = {
                'date': session.date,
                'attendance_type': session.attendance_type,
                'class_level_id': session.class_level_id,
                'stream_id': session.stream_id,
                'subject_id': session.subject_id if session.subject else None,
                'period': session.period,
                'is_subject_type': session.attendance_type == 'SUBJECT',
                'class_name': session.class_level.name if session.class_level else None,
                'stream_name': session.stream.stream_letter if session.stream else None,
                'subject_name': session.subject.name if session.subject else None,
                'created_at': session.created_at if hasattr(session, 'created_at') else None,
                'updated_at': session.updated_at if hasattr(session, 'updated_at') else None,
                'is_draft': session.is_draft if hasattr(session, 'is_draft') else False
            }
            
        except AttendanceSession.DoesNotExist:
            context['session_data'] = None
        
        context['session_id'] = session_id
        
        return context
    

@method_decorator(csrf_exempt, name='dispatch')
class UpdateAttendanceSessionAPI(AdminRequiredMixin, View):
    """API to update attendance session"""
    def post(self, request, session_id):
        try:
            data = json.loads(request.body)
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # Update session details
            session.date = data.get('date', session.date)
            session.attendance_type = data.get('attendance_type', session.attendance_type)
            session.period = data.get('period', session.period)
            
            if 'class_level' in data:
                session.class_level_id = data['class_level']
            if 'stream' in data:
                session.stream_id = data['stream']
            if 'subject' in data:
                session.subject_id = data['subject']
            
            session.save()
            
            # Update student attendance
            if 'student_attendance' in data:
                student_attendance_data = data['student_attendance']
                current_attendance = StudentAttendance.objects.filter(
                    attendance_session=session
                )
                
                # Create list of student IDs from request
                request_student_ids = set(map(str, student_attendance_data.keys()))
                
                # Get existing attendance records
                existing_attendance = {
                    str(att.student_id): att 
                    for att in current_attendance
                }
                
                # Update or create attendance records
                attendance_objects = []
                for student_id_str, attendance_data in student_attendance_data.items():
                    student_id = int(student_id_str)
                    
                    if student_id_str in existing_attendance:
                        # Update existing record
                        att = existing_attendance[student_id_str]
                        att.status = attendance_data.get('status', 'A')
                        att.remark = attendance_data.get('remark', '')
                        att.save()
                    else:
                        # Create new record
                        attendance_objects.append(
                            StudentAttendance(
                                attendance_session=session,
                                student_id=student_id,
                                status=attendance_data.get('status', 'A'),
                                remark=attendance_data.get('remark', '')
                            )
                        )
                
                # Bulk create new records
                if attendance_objects:
                    StudentAttendance.objects.bulk_create(attendance_objects)
                
                # Delete records for students no longer in the list
                existing_student_ids = set(existing_attendance.keys())
                students_to_delete = existing_student_ids - request_student_ids
                if students_to_delete:
                    StudentAttendance.objects.filter(
                        attendance_session=session,
                        student_id__in=[int(id) for id in students_to_delete]
                    ).delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance session updated successfully'
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class GetEditAttendanceSessionAPI(AdminRequiredMixin, View):
    """API to get session data for editing"""
    def get(self, request, session_id):
        try:
            session = get_object_or_404(
                AttendanceSession.objects.select_related(
                    'class_level', 'stream', 'subject'
                ),
                id=session_id
            )
            
            # Get session details
            session_data = {
                'id': session.id,
                'date': session.date.strftime('%Y-%m-%d'),
                'attendance_type': session.attendance_type,
                'class_level_id': session.class_level_id,
                'stream_id': session.stream_id,
                'subject_id': session.subject_id if session.subject else None,
                'period': session.period,
                'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else None,
                'is_draft': getattr(session, 'is_draft', False)  # Add this line if your model has is_draft field
            }
            
            # Get student attendance for this session
            student_attendance = StudentAttendance.objects.filter(
                attendance_session=session
            ).select_related('student')
            
            attendance_data = {}
            for attendance in student_attendance:
                attendance_data[str(attendance.student_id)] = {
                    'status': attendance.status,
                    'remark': attendance.remark or ''
                }
            
            return JsonResponse({
                'success': True,
                'session': session_data,
                'student_attendance': attendance_data
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class EditAttendanceSessionAPI(AdminRequiredMixin, View):
    def get(self, request, session_id):
        try:
            session = get_object_or_404(
                AttendanceSession.objects.select_related(
                    'class_level', 'stream', 'subject'
                ),
                id=session_id
            )
            
            # Get session details
            session_data = {
                'id': session.id,
                'date': session.date.strftime('%Y-%m-%d'),
                'attendance_type': session.attendance_type,
                'class_level_id': session.class_level_id,
                'stream_id': session.stream_id,
                'subject_id': session.subject_id,
                'period': session.period,
                'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S') if session.created_at else None
            }
            
            # Get student attendance for this session
            student_attendance = StudentAttendance.objects.filter(
                attendance_session=session
            ).select_related('student')
            
            attendance_data = {}
            for attendance in student_attendance:
                attendance_data[str(attendance.student_id)] = {
                    'status': attendance.status,
                    'remark': attendance.remark or ''
                }
            
            return JsonResponse({
                'success': True,
                'session': session_data,
                'student_attendance': attendance_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    def post(self, request, session_id):
        try:
            data = json.loads(request.body)
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # Check if we're duplicating or updating
            action = data.get('action')
            
            if action == 'duplicate_session':
                return self.duplicate_session(data)
            
            # Update session details
            session.date = data.get('date', session.date)
            session.attendance_type = data.get('attendance_type', session.attendance_type)
            session.period = data.get('period', session.period)
            
            if 'class_level' in data:
                session.class_level_id = data['class_level']
            if 'stream' in data:
                session.stream_id = data['stream']
            if 'subject' in data:
                session.subject_id = data['subject']
            
            session.save()
            
            # Update student attendance
            if 'student_attendance' in data:
                student_attendance_data = data['student_attendance']
                current_attendance = StudentAttendance.objects.filter(
                    attendance_session=session
                )
                
                # Create list of student IDs from request
                request_student_ids = set(map(str, student_attendance_data.keys()))
                
                # Get existing attendance records
                existing_attendance = {
                    str(att.student_id): att 
                    for att in current_attendance
                }
                
                # Update or create attendance records
                attendance_objects = []
                for student_id_str, attendance_data in student_attendance_data.items():
                    student_id = int(student_id_str)
                    
                    if student_id_str in existing_attendance:
                        # Update existing record
                        att = existing_attendance[student_id_str]
                        att.status = attendance_data.get('status', 'A')
                        att.remark = attendance_data.get('remark', '')
                        att.save()
                    else:
                        # Create new record
                        attendance_objects.append(
                            StudentAttendance(
                                attendance_session=session,
                                student_id=student_id,
                                status=attendance_data.get('status', 'A'),
                                remark=attendance_data.get('remark', '')
                            )
                        )
                
                # Bulk create new records
                if attendance_objects:
                    StudentAttendance.objects.bulk_create(attendance_objects)
                
                # Delete records for students no longer in the list
                existing_student_ids = set(existing_attendance.keys())
                students_to_delete = existing_student_ids - request_student_ids
                if students_to_delete:
                    StudentAttendance.objects.filter(
                        attendance_session=session,
                        student_id__in=[int(id) for id in students_to_delete]
                    ).delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance session updated successfully'
            })
            
        except Exception as e:
            import traceback
            return JsonResponse({
                'success': False,
                'message': str(e),
                'traceback': traceback.format_exc()
            }, status=400)
    
    def duplicate_session(self, data):
        """Duplicate an attendance session"""
        try:
            # Create new attendance session
            new_session = AttendanceSession.objects.create(
                date=data['date'],
                attendance_type=data['attendance_type'],
                class_level_id=data['class_level'],
                stream_id=data['stream'],
                subject_id=data.get('subject'),
                period=data.get('period')
            )
            
            # Create student attendance records
            student_attendance_data = data.get('student_attendance', {})
            student_attendance_objects = []
            
            for student_id, attendance_data in student_attendance_data.items():
                student_attendance_objects.append(
                    StudentAttendance(
                        attendance_session=new_session,
                        student_id=student_id,
                        status=attendance_data.get('status', 'A'),
                        remark=attendance_data.get('remark', '')
                    )
                )
            
            # Bulk create student attendance records
            if student_attendance_objects:
                StudentAttendance.objects.bulk_create(student_attendance_objects)
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance session duplicated successfully',
                'session_id': new_session.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)




# Edit Session API
@method_decorator(csrf_exempt, name='dispatch')
class EditAttendanceSessionAPI(AdminRequiredMixin, View):
    def get(self, request, session_id):
        try:
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # Get session details
            session_data = {
                'id': session.id,
                'date': session.date.strftime('%Y-%m-%d'),
                'attendance_type': session.attendance_type,
                'class_level_id': session.class_level_id,
                'stream_id': session.stream_id,
                'subject_id': session.subject_id,
                'period': session.period,              
            }
            
            # Get student attendance for this session
            student_attendance = StudentAttendance.objects.filter(
                attendance_session=session
            ).select_related('student')
            
            attendance_data = {}
            for attendance in student_attendance:
                attendance_data[str(attendance.student_id)] = {
                    'status': attendance.status,
                    'remark': attendance.remark or ''
                }
            
            return JsonResponse({
                'success': True,
                'session': session_data,
                'student_attendance': attendance_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    def post(self, request, session_id):
        try:
            data = json.loads(request.body)
            session = get_object_or_404(AttendanceSession, id=session_id)
            
            # Update session details
            for field in ['date', 'attendance_type', 'period']:
                if field in data:
                    setattr(session, field, data[field])
            
            if 'class_level' in data:
                session.class_level_id = data['class_level']
            if 'stream' in data:
                session.stream_id = data['stream']
            if 'subject' in data:
                session.subject_id = data['subject']
          
            
            session.save()
            
            # Update student attendance
            if 'student_attendance' in data:
                for student_id, attendance_data in data['student_attendance'].items():
                    StudentAttendance.objects.update_or_create(
                        attendance_session=session,
                        student_id=student_id,
                        defaults={
                            'status': attendance_data.get('status', 'A'),
                            'remark': attendance_data.get('remark', '')
                        }
                    )
            
            return JsonResponse({
                'success': True,
                'message': 'Attendance session updated successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)


class StudentAttendanceListView(AdminRequiredMixin, TemplateView):
    """View to list all students with attendance summary"""
    template_name = 'admin/attendance/student_attendance_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter parameters
        class_filter = self.request.GET.get('class_level', '')
        stream_filter = self.request.GET.get('stream', '')
        status_filter = self.request.GET.get('status', '')
        search_filter = self.request.GET.get('search', '')
        
        # Base queryset - get ALL students
        students = Student.objects.all().select_related(
            'class_level', 'stream_class'
        ).order_by('class_level__name', 'last_name', 'first_name')
        
        # Apply filters
        if class_filter:
            students = students.filter(class_level_id=class_filter)
        if stream_filter:
            students = students.filter(stream_class_id=stream_filter)
        if status_filter:
            if status_filter == 'active':
                students = students.filter(is_active=True)
            elif status_filter == 'inactive':
                students = students.filter(is_active=False)
        if search_filter:
            students = students.filter(
                Q(first_name__icontains=search_filter) |
                Q(last_name__icontains=search_filter) |
                Q(registration_number__icontains=search_filter) |
                Q(email__icontains=search_filter)
            )
        
        # Add attendance count annotation
        students = students.annotate(
            attendance_count=Count('studentattendance', distinct=True)
        )
        
        # Prepare context
        context['students'] = students
        context['class_levels'] = ClassLevel.objects.all()
        context['filter_class'] = class_filter
        context['filter_stream'] = stream_filter
        context['filter_status'] = status_filter
        context['filter_search'] = search_filter
        
        # Get streams for selected class
        if class_filter:
            context['streams'] = StreamClass.objects.filter(
                class_level_id=class_filter, 
                is_active=True
            )
        else:
            # Empty queryset if no class selected
            context['streams'] = StreamClass.objects.none()
        
        return context


# attendance/views.py (add this to your existing views)

class StudentAttendanceReportView(AdminRequiredMixin, TemplateView):
    """Detailed student attendance report with filtering"""
    template_name = 'admin/attendance/student_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get student
        student_id = self.kwargs.get('student_id')
        student = get_object_or_404(
            Student.objects.select_related('class_level', 'stream_class'),
            id=student_id
        )
        
        # Get filter parameters
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        attendance_type = self.request.GET.get('attendance_type', 'ALL')
        status_filter = self.request.GET.get('status', 'ALL')
        
        # Default to current academic year if no dates provided
        current_year = timezone.now().year
        academic_start = datetime(current_year, 1, 1).date()  # Jan 1 of current year
        academic_end = datetime(current_year, 12, 31).date()  # Dec 31 of current year
        
        if not start_date:
            start_date = academic_start.strftime('%Y-%m-%d')
        if not end_date:
            end_date = academic_end.strftime('%Y-%m-%d')
        
        # Convert dates
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date_obj = academic_start
            end_date_obj = academic_end
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        # Get attendance records with filters
        attendance_records = StudentAttendance.objects.filter(
            student=student,
            attendance_session__date__gte=start_date_obj,
            attendance_session__date__lte=end_date_obj
        ).select_related(
            'attendance_session__class_level',
            'attendance_session__stream',
            'attendance_session__subject'
        ).order_by('-attendance_session__date', '-attendance_session__period')
        
        # Apply additional filters
        if attendance_type and attendance_type != 'ALL':
            attendance_records = attendance_records.filter(
                attendance_session__attendance_type=attendance_type
            )
        
        if status_filter and status_filter != 'ALL':
            attendance_records = attendance_records.filter(status=status_filter)
        
        # Calculate statistics
        stats = attendance_records.aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='P')),
            absent=Count('id', filter=Q(status='A')),
            late=Count('id', filter=Q(status='L')),
            excused=Count('id', filter=Q(status='E'))
        )
        
        # Calculate attendance rate
        attendance_rate = 0
        if stats['total'] and stats['total'] > 0:
            attendance_rate = round((stats['present'] / stats['total']) * 100, 2)
        
        # Group by date for daily summary
        daily_summary = {}
        for record in attendance_records:
            date_str = record.attendance_session.date.strftime('%Y-%m-%d')
            if date_str not in daily_summary:
                daily_summary[date_str] = {
                    'date': record.attendance_session.date,
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0,
                    'sessions': []
                }
            
            daily_summary[date_str]['total'] += 1
            if record.status == 'P':
                daily_summary[date_str]['present'] += 1
            elif record.status == 'A':
                daily_summary[date_str]['absent'] += 1
            elif record.status == 'L':
                daily_summary[date_str]['late'] += 1
            elif record.status == 'E':
                daily_summary[date_str]['excused'] += 1
            
            daily_summary[date_str]['sessions'].append(record)
        
        # Sort daily summary by date
        sorted_daily_summary = sorted(
            daily_summary.values(), 
            key=lambda x: x['date'], 
            reverse=True
        )
        
        # Calculate monthly trends
        monthly_trends = self.calculate_monthly_trends(student, start_date_obj, end_date_obj)
        
        context['student'] = student
        context['attendance_records'] = attendance_records
        context['stats'] = stats
        context['attendance_rate'] = attendance_rate
        context['daily_summary'] = sorted_daily_summary
        context['monthly_trends'] = monthly_trends
        context['total_days'] = len(daily_summary)
        context['total_sessions'] = stats['total'] or 0
        
        # Filter parameters
        context['start_date'] = start_date
        context['end_date'] = end_date
        context['attendance_type_filter'] = attendance_type
        context['status_filter'] = status_filter
        
        # Filter options
        context['attendance_types'] = [
            ('ALL', 'All Types'),
            ('CLASS', 'Class Wise'),
            ('SUBJECT', 'Subject Wise')
        ]
        
        context['status_options'] = [
            ('ALL', 'All Status'),
            ('P', 'Present'),
            ('A', 'Absent'),
            ('L', 'Late'),
            ('E', 'Excused')
        ]
        
        return context
    
    def calculate_monthly_trends(self, student, start_date, end_date):
        """Calculate monthly attendance trends"""
        monthly_data = []
        
        # Generate months between start and end date
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            month_start = current_date
            if current_date.month == 12:
                month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
            
            # Get attendance for this month
            month_records = StudentAttendance.objects.filter(
                student=student,
                attendance_session__date__gte=month_start,
                attendance_session__date__lte=month_end
            )
            
            month_stats = month_records.aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='P')),
                absent=Count('id', filter=Q(status='A')),
                late=Count('id', filter=Q(status='L')),
                excused=Count('id', filter=Q(status='E'))
            )
            
            attendance_rate = 0
            if month_stats['total'] and month_stats['total'] > 0:
                attendance_rate = round((month_stats['present'] / month_stats['total']) * 100, 2)
            
            monthly_data.append({
                'month': month_start.strftime('%B %Y'),
                'start_date': month_start,
                'stats': month_stats,
                'attendance_rate': attendance_rate,
                'total_days': month_records.values('attendance_session__date').distinct().count()
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1, day=1)
        
        return monthly_data


class DownloadAttendancePDFView(AdminRequiredMixin, View):
    """Generate and download PDF attendance report using WeasyPrint"""
    
    def get(self, request, student_id):
        try:
            # Get student
            student = get_object_or_404(
                Student.objects.select_related('class_level', 'stream_class'),
                id=student_id
            )
            
            # Get filter parameters from request
            start_date = request.GET.get('start_date', '')
            end_date = request.GET.get('end_date', '')
            attendance_type = request.GET.get('attendance_type', 'ALL')
            status_filter = request.GET.get('status', 'ALL')
            
            # Default to current academic year if no dates provided
            current_year = timezone.now().year
            academic_start = datetime(current_year, 1, 1).date()
            academic_end = datetime(current_year, 12, 31).date()
            
            if not start_date:
                start_date = academic_start.strftime('%Y-%m-%d')
            if not end_date:
                end_date = academic_end.strftime('%Y-%m-%d')
            
            # Convert dates
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                start_date_obj = academic_start
                end_date_obj = academic_end
            
            # Get attendance records with filters (same logic as report view)
            attendance_records = StudentAttendance.objects.filter(
                student=student,
                attendance_session__date__gte=start_date_obj,
                attendance_session__date__lte=end_date_obj
            ).select_related(
                'attendance_session__class_level',
                'attendance_session__stream',
                'attendance_session__subject'
            ).order_by('-attendance_session__date', '-attendance_session__period')
            
            if attendance_type and attendance_type != 'ALL':
                attendance_records = attendance_records.filter(
                    attendance_session__attendance_type=attendance_type
                )
            
            if status_filter and status_filter != 'ALL':
                attendance_records = attendance_records.filter(status=status_filter)
            
            # Calculate statistics
            stats = attendance_records.aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='P')),
                absent=Count('id', filter=Q(status='A')),
                late=Count('id', filter=Q(status='L')),
                excused=Count('id', filter=Q(status='E'))
            )
            
            attendance_rate = 0
            if stats['total'] and stats['total'] > 0:
                attendance_rate = round((stats['present'] / stats['total']) * 100, 2)
            
            # Group by date for daily summary
            daily_summary = {}
            for record in attendance_records:
                date_str = record.attendance_session.date.strftime('%Y-%m-%d')
                if date_str not in daily_summary:
                    daily_summary[date_str] = {
                        'date': record.attendance_session.date,
                        'total': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0,
                        'sessions': []
                    }
                
                daily_summary[date_str]['total'] += 1
                if record.status == 'P':
                    daily_summary[date_str]['present'] += 1
                elif record.status == 'A':
                    daily_summary[date_str]['absent'] += 1
                elif record.status == 'L':
                    daily_summary[date_str]['late'] += 1
                elif record.status == 'E':
                    daily_summary[date_str]['excused'] += 1
            
            # Sort daily summary by date
            sorted_daily_summary = sorted(
                daily_summary.values(), 
                key=lambda x: x['date'], 
                reverse=True
            )
            
            # Calculate monthly trends (for PDF only if needed)
            monthly_trends = []
            current_date = start_date_obj.replace(day=1)
            while current_date <= end_date_obj:
                month_start = current_date
                if current_date.month == 12:
                    month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
                
                month_records = attendance_records.filter(
                    attendance_session__date__gte=month_start,
                    attendance_session__date__lte=month_end
                )
                
                month_stats = month_records.aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='P')),
                    absent=Count('id', filter=Q(status='A')),
                    late=Count('id', filter=Q(status='L')),
                    excused=Count('id', filter=Q(status='E'))
                )
                
                month_rate = 0
                if month_stats['total'] and month_stats['total'] > 0:
                    month_rate = round((month_stats['present'] / month_stats['total']) * 100, 2)
                
                monthly_trends.append({
                    'month': month_start.strftime('%B %Y'),
                    'stats': month_stats,
                    'attendance_rate': month_rate,
                    'total_days': month_records.values('attendance_session__date').distinct().count()
                })
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1, day=1)
            
            # Prepare context for template
            context = {
                'student': student,
                'start_date': start_date,
                'end_date': end_date,
                'attendance_records': attendance_records,
                'stats': stats,
                'attendance_rate': attendance_rate,
                'daily_summary': sorted_daily_summary,
                'monthly_trends': monthly_trends,
                'total_days': len(daily_summary),
                'total_sessions': stats['total'] or 0,
                'attendance_type_filter': attendance_type,
                'status_filter': status_filter,
                'generation_date': timezone.now().strftime('%B %d, %Y %I:%M %p'),
                'school_name': 'YOUR SCHOOL NAME',  # Add your school name here
                'school_address': 'YOUR SCHOOL ADDRESS',  # Add your school address here
            }
            
            # Render HTML template
            html_string = render_to_string('admin/attendance/pdf_report.html', context)
            
            # Configure fonts
            font_config = FontConfiguration()
            
            # Generate PDF
            html = HTML(string=html_string)
            pdf_file = html.write_pdf(font_config=font_config)
            
            # Create HTTP response with PDF
            response = HttpResponse(pdf_file, content_type='application/pdf')
            
            # Create filename
            filename = f"attendance_report_{student.registration_number or student.id}_{start_date}_to_{end_date}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            import traceback
            print(f"Error generating PDF: {e}")
            print(traceback.format_exc())
            
            # Return error response
            messages.error(request, f"Error generating PDF: {str(e)}")
            return redirect('student_attendance_report', student_id=student_id) 