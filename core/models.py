from django.db import models
from django.core.exceptions import ValidationError


class EducationalLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)  # PRIMARY, O_LEVEL, A_LEVEL
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Educational Level'
        verbose_name_plural = 'Educational Levels'

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    """
    Academic Year mfano: 2024/2025, 2025/2026
    Inatumika kwa Nursery, Primary, O-Level, A-Level
    """

    name = models.CharField(
        max_length=9,
        unique=True,
        help_text="Mfano: 2024/2025"
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(
        default=False,
        help_text="Ni mwaka unaotumika kwa sasa"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"

    def __str__(self):
        return self.name

    def clean(self):
        """Hakikisha tarehe zinafuatana vizuri"""
        if self.start_date >= self.end_date:
            raise ValidationError("Start date lazima iwe kabla ya end date")

    def save(self, *args, **kwargs):
        """
        Hakikisha kuna AcademicYear MOJA TU active
        """
        if self.is_active:
            AcademicYear.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Term(models.Model):
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='terms'
    )
    term_number = models.IntegerField(choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('academic_year', 'term_number')
        ordering = ['academic_year', 'term_number']

    def __str__(self):
        return f"{self.get_term_number_display()} - {self.academic_year}"

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("Start date lazima iwe kabla ya end date")

        if self.start_date < self.academic_year.start_date:
            raise ValidationError("Term inaanza nje ya AcademicYear")

        if self.end_date > self.academic_year.end_date:
            raise ValidationError("Term inaisha nje ya AcademicYear")

    def save(self, *args, **kwargs):
        if self.is_active:
            Term.objects.filter(
                academic_year=self.academic_year
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class Subject(models.Model):
    educational_level = models.ForeignKey(
        EducationalLevel,
        on_delete=models.CASCADE,
        related_name='subjects'
    )

    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=20, blank=True)
    code = models.CharField(max_length=20)

    is_compulsory = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('educational_level', 'code')
        ordering = ['educational_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.educational_level.code})"


class ClassLevel(models.Model):
    """
    Represents a class within an educational level
    Example:
    - Nursery → Baby, KG1, KG2
    - Primary → Std 1 – Std 7
    - O-Level → Form 1 – Form 4
    - A-Level → Form 5 – Form 6
    """

    educational_level = models.ForeignKey(
        EducationalLevel,
        on_delete=models.CASCADE,
        related_name='class_levels'
    )

    name = models.CharField(max_length=50)   # e.g. "Form 1", "Std 3"
    code = models.CharField(max_length=20)   # e.g. "F1", "STD3"
    order = models.PositiveIntegerField()    # for proper ordering
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['educational_level', 'order']
        unique_together = ('educational_level', 'code')
        verbose_name = 'Class Level'
        verbose_name_plural = 'Class Levels'

    def __str__(self):
        return f"{self.name} - {self.educational_level}"




class StreamClass(models.Model):
    """
    Represents a class stream, e.g., Form 1A, Form 2B, Std 3C
    Linked to ClassLevel and optionally to a class teacher (Staff)
    """

    class_level = models.ForeignKey(
        'ClassLevel',
        on_delete=models.CASCADE,
        related_name='streams'
    )

    stream_letter = models.CharField(
        max_length=1,
        help_text="A, B, C etc."
    )

    capacity = models.PositiveIntegerField(default=50)


    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('class_level', 'stream_letter')
        ordering = ['class_level', 'stream_letter']
        verbose_name = "Stream Class"
        verbose_name_plural = "Stream Classes"

    def __str__(self):
        return f"{self.class_level.name}{self.stream_letter}"

    @property
    def student_count(self):
        return self.students.filter(status='active').count()
    

class Combination(models.Model):
    educational_level = models.ForeignKey(
        EducationalLevel,
        on_delete=models.CASCADE,
        limit_choices_to={'code': 'A_LEVEL'}
    )

    name = models.CharField(max_length=50)   # PCM, PCB
    code = models.CharField(max_length=10, unique=True)

    subjects = models.ManyToManyField(
        Subject,
        through='CombinationSubject'
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class CombinationSubject(models.Model):
    SUBJECT_ROLE_CHOICES = [
        ('CORE', 'Core Subject'),
        ('SUB', 'Subsidiary Subject'),
    ]

    combination = models.ForeignKey(Combination, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    role = models.CharField(max_length=5, choices=SUBJECT_ROLE_CHOICES)

    class Meta:
        unique_together = ('combination', 'subject')
