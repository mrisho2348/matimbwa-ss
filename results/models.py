# results/models.py
from django.db import models
from django.core.exceptions import ValidationError
from core.models import Term, ClassLevel, StreamClass, Subject, EducationalLevel, AcademicYear
from django.core.validators import MinValueValidator, MaxValueValidator
from students.models import Student


class GradingScale(models.Model):
    """
    Unified grading scale based on Education Level
    """

    GRADE_CHOICES = [
        ('A', 'A - Excellent'),
        ('B', 'B - Very Good'),
        ('C', 'C - Good'),
        ('D', 'D - Satisfactory'),
        ('E', 'E - Fair'),
        ('F', 'F - Fail'),
        ('S', 'S - Subsidiary'),
    ]

    education_level = models.ForeignKey(
        EducationalLevel,
        on_delete=models.CASCADE,
        related_name='grading_scales'
    )

    grade = models.CharField(max_length=1, choices=GRADE_CHOICES)

    min_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    max_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    points = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0,
        help_text="Grade points (0 for primary)"
    )

    description = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['education_level', '-min_mark']
        unique_together = ('education_level', 'grade')
        verbose_name = 'Grading Scale'
        verbose_name_plural = 'Grading Scales'

    def clean(self):
        if self.min_mark > self.max_mark:
            raise ValidationError("Minimum mark cannot exceed maximum mark")

    def __str__(self):
        return (
            f"{self.education_level.name} | "
            f"{self.grade} ({self.min_mark}-{self.max_mark}) "
            f"Points: {self.points}"
        )


class DivisionScale(models.Model):
    """
    Division / GPA scale based on total points
    Used for O-Level and A-Level
    """

    DIVISION_CHOICES = [
        ('I', 'Division I'),
        ('II', 'Division II'),
        ('III', 'Division III'),
        ('IV', 'Division IV'),
        ('0', 'Division 0'),
    ]

    education_level = models.ForeignKey(
        EducationalLevel,
        on_delete=models.CASCADE,
        related_name='division_scales'
    )

    min_points = models.PositiveIntegerField()
    max_points = models.PositiveIntegerField()

    division = models.CharField(
        max_length=5,
        choices=DIVISION_CHOICES
    )

    class Meta:
        ordering = ['min_points']
        unique_together = ('education_level', 'division')
        verbose_name = 'Division Scale'
        verbose_name_plural = 'Division Scales'

    def clean(self):
        if self.min_points > self.max_points:
            raise ValidationError("Min points cannot exceed max points")

    def __str__(self):
        return (
            f"{self.education_level.name} | "
            f"{self.division} ({self.min_points}-{self.max_points})"
        )


class ExamType(models.Model):
    """
    Defines the type of examination and how it contributes
    to final results.
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Contribution (%) of this exam to the final score"
    )

    max_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Maximum obtainable marks for this exam"
    )

    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Exam Type'
        verbose_name_plural = 'Exam Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class ExamSession(models.Model):
    """
    One exam event containing multiple subjects
    Example: Form 2 Midterm Term I 2025
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('published', 'Published'),
    ]

    name = models.CharField(max_length=200)
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE)
    stream_class = models.ForeignKey(StreamClass, null=True, blank=True, on_delete=models.CASCADE)

    exam_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.class_level}"


class ExamPaper(models.Model):
    """
    A subject paper under an exam session
    """
    exam_session = models.ForeignKey(
        ExamSession,
        on_delete=models.CASCADE,
        related_name='papers'
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    total_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100
    )

    class Meta:
        unique_together = ['exam_session', 'subject']

    def __str__(self):
        return f"{self.exam_session} - {self.subject}"


class StudentResult(models.Model):
    exam_paper = models.ForeignKey(
        ExamPaper,
        on_delete=models.CASCADE,
        related_name='results'
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    grade = models.CharField(max_length=2, blank=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    # New fields for student position
    position_in_paper = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['exam_paper', 'student']
        ordering = ['-marks_obtained']

    def __str__(self):
        return f"{self.student.full_name} | {self.exam_paper} | {self.marks_obtained or 'ABS'}"


# ============== STUDENT EXAM METRICS ==============
class StudentExamMetrics(models.Model):
    """
    Stores calculated metrics for a student in an exam session:
    - total marks
    - average marks
    - average percentage
    - total grade points (O-Level / A-Level)
    - division (based on division scale)
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_metrics')
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='student_metrics')

    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    average_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    total_grade_points = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    division = models.ForeignKey(DivisionScale, null=True, blank=True, on_delete=models.SET_NULL)

    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'exam_session']
        verbose_name = 'Student Exam Metrics'
        verbose_name_plural = 'Student Exam Metrics'

    def __str__(self):
        return f"{self.student.full_name} - {self.exam_session}"

    def calculate_metrics(self):
        """
        Calculates metrics for the student for this exam session:
        - total_marks
        - average_marks
        - average_percentage
        - total_grade_points based on best 7 subjects (if O-Level)
        - division based on total points
        """
        from django.db.models import Sum, F, Q

        results = StudentResult.objects.filter(exam_paper__exam_session=self.exam_session, student=self.student)
        present_results = results.filter(marks_obtained__isnull=False)

        # Total Marks
        self.total_marks = present_results.aggregate(total=Sum('marks_obtained'))['total'] or 0

        # Average Marks & Percentage
        if present_results.exists():
            self.average_marks = self.total_marks / present_results.count()
            total_max_marks = present_results.aggregate(
                total=Sum(F('exam_paper__total_marks'))
            )['total'] or 0
            if total_max_marks > 0:
                self.average_percentage = (self.total_marks / total_max_marks) * 100

        # Total grade points (best 7 subjects for secondary/advanced)
        education_level = self.exam_session.class_level.education_level
        if education_level.name.lower() in ['secondary', 'advanced']:
            # Best 7 subjects by grade points
            results_with_points = present_results.filter(grade_point__isnull=False).order_by('-grade_point')
            top_subjects = list(results_with_points[:7])
            self.total_grade_points = sum([r.grade_point or 0 for r in top_subjects])

            # Assign division based on division scale
            if self.total_grade_points is not None:
                division = DivisionScale.objects.filter(
                    education_level=education_level,
                    min_points__lte=self.total_grade_points,
                    max_points__gte=self.total_grade_points
                ).first()
                self.division = division

        self.save()


# ============== STUDENT EXAM POSITION ==============
class StudentExamPosition(models.Model):
    """
    Stores student positions for an exam session:
    - class-wise position
    - stream-wise position (optional)
    - calculated based on average percentage or metrics
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_positions')
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='exam_positions')

    class_position = models.PositiveIntegerField(null=True, blank=True)
    stream_position = models.PositiveIntegerField(null=True, blank=True)

    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'exam_session']
        verbose_name = 'Student Exam Position'
        verbose_name_plural = 'Student Exam Positions'

    def __str__(self):
        return f"{self.student.full_name} - {self.exam_session}"

    def calculate_positions(self):
        """
        Calculates class-wise and stream-wise positions based on
        StudentExamMetrics.average_percentage
        """
        from django.db.models import F, Window
        from django.db.models.functions import DenseRank

        # Get all metrics for the same exam session
        metrics_qs = StudentExamMetrics.objects.filter(exam_session=self.exam_session, average_percentage__isnull=False)

        # Class-wise ranking
        class_ranked = metrics_qs.annotate(
            rank=Window(
                expression=DenseRank(),
                order_by=F('average_percentage').desc()
            )
        )
        for metric in class_ranked:
            pos, _ = StudentExamPosition.objects.get_or_create(student=metric.student, exam_session=self.exam_session)
            pos.class_position = metric.rank
            pos.save()

        # Stream-wise ranking (if applicable)
        if self.exam_session.stream_class:
            stream_qs = metrics_qs.filter(student__stream_class=self.exam_session.stream_class)
            stream_ranked = stream_qs.annotate(
                rank=Window(
                    expression=DenseRank(),
                    order_by=F('average_percentage').desc()
                )
            )
            for metric in stream_ranked:
                pos = StudentExamPosition.objects.get(student=metric.student, exam_session=self.exam_session)
                pos.stream_position = metric.rank
                pos.save()
