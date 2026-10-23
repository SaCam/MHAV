"""Django admin for MHAV course planning and applications."""
from django.contrib import admin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Season, Dog, Combination, TrainingGroup, LessonInstructorOverride,
    Enrollment, CourseApplication, TrainerSeasonAvailability, SeasonCourseOffering,
    RegistrationPayment, RegistrationPaymentEvent, StripeCheckoutAttempt,
)


class TrainingGroupInline(admin.TabularInline):
    model = TrainingGroup
    extra = 0
    fields = ('name', 'course', 'trainer', 'day', 'starts_at', 'ends_at', 'capacity')
    show_change_link = True


class OfferingInline(admin.TabularInline):
    model = SeasonCourseOffering
    extra = 0
    fields = ('course', 'approved', 'registration_open', 'waiting_list_enabled')
    show_change_link = True


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'starts_on', 'ends_on', 'status', 'lesson_count', 'group_total', 'application_total')
    list_filter = ('status', 'starts_on')
    search_fields = ('name',)
    list_editable = ('status',)
    ordering = ('-starts_on',)
    inlines = (OfferingInline, TrainingGroupInline)
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_groups=Count('groups', distinct=True), _applications=Count('applications', distinct=True))
    @admin.display(description='Lesgroepen', ordering='_groups')
    def group_total(self, obj): return obj._groups
    @admin.display(description='Aanvragen', ordering='_applications')
    def application_total(self, obj): return obj._applications


@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ('name', 'breed', 'date_of_birth', 'combination_total')
    search_fields = ('name', 'breed', 'combinations__handler__username')
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_combinations=Count('combinations'))
    @admin.display(description='Combinaties', ordering='_combinations')
    def combination_total(self, obj): return obj._combinations


@admin.register(Combination)
class CombinationAdmin(admin.ModelAdmin):
    list_display = ('handler', 'dog', 'enrollment_total')
    list_select_related = ('handler', 'dog')
    search_fields = ('handler__username', 'handler__first_name', 'handler__last_name', 'handler__email', 'dog__name')
    autocomplete_fields = ('dog',)
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_enrollments=Count('enrollments'))
    @admin.display(description='Inschrijvingen', ordering='_enrollments')
    def enrollment_total(self, obj): return obj._enrollments


class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    extra = 0
    fields = ('combination', 'status', 'notes')
    show_change_link = True
    autocomplete_fields = ('combination',)


class InstructorOverrideInline(admin.TabularInline):
    model = LessonInstructorOverride
    extra = 0
    fields = ('lesson_date', 'trainer', 'offline_confirmed')
    show_change_link = True


@admin.register(TrainingGroup)
class TrainingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'season', 'course', 'trainer', 'day', 'starts_at', 'capacity', 'placed_total', 'free_places')
    list_filter = ('season', 'course', 'day')
    search_fields = ('name', 'course__title', 'season__name', 'trainer__username')
    list_select_related = ('season', 'course', 'trainer')
    autocomplete_fields = ('course',)
    inlines = (EnrollmentInline, InstructorOverrideInline)
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_placed=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.PLACED)))
    @admin.display(description='Geplaatst', ordering='_placed')
    def placed_total(self, obj): return obj._placed
    @admin.display(description='Vrije plaatsen')
    def free_places(self, obj): return max(0, obj.capacity - obj._placed)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('combination', 'group', 'status', 'created_at')
    list_filter = ('status', 'group__season', 'group__course')
    search_fields = ('combination__dog__name', 'combination__handler__username', 'group__name')
    list_select_related = ('combination__dog', 'combination__handler', 'group__season')
    autocomplete_fields = ('group', 'combination')
    readonly_fields = ('created_at',)
    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.register(CourseApplication)
class CourseApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant', 'dog_name', 'course', 'season', 'status', 'proposed_group', 'linked_enrollment', 'created_at', 'planning_link')
    list_filter = ('status', 'season', 'course', 'created_at')
    search_fields = ('first_name', 'middle_name', 'last_name', 'email', 'phone', 'dog_name', 'dog_breed')
    list_select_related = ('course', 'season', 'proposed_group', 'linked_enrollment')
    readonly_fields = ('created_at', 'updated_at', 'privacy_accepted_at', 'planning_link')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_per_page = 40
    fieldsets = (
        ('Aanvraag en planning', {'fields': ('status', 'course', 'season', 'proposed_group', 'linked_combination', 'linked_enrollment', 'admin_notes', 'planning_link')}),
        ('Aanvrager', {'fields': ('user', 'first_name', 'middle_name', 'last_name', 'email', 'phone', 'street', 'house_number', 'postal_code', 'city', 'country')}),
        ('Hond', {'fields': ('dog_name', 'dog_breed', 'dog_birth_date', 'dog_sex', 'dog_origin', 'dog_pedigree', 'dog_count', 'first_dog', 'trained_before', 'dog_notes')}),
        ('Voorkeuren en opmerkingen', {'fields': ('time_preferences', 'availability', 'experience', 'remarks')}),
        ('Administratie', {'classes': ('collapse',), 'fields': ('created_at', 'updated_at', 'privacy_accepted_at')}),
    )
    @admin.display(description='Aanvrager')
    def applicant(self, obj):
        return ' '.join(filter(None, (obj.first_name, obj.middle_name, obj.last_name)))
    @admin.display(description='Planning')
    def planning_link(self, obj):
        if not obj.pk: return 'Sla eerst de aanvraag op'
        return format_html('<a href="{}">Open in cursusadministratie ↗</a>', reverse('planning:application_detail', args=[obj.pk]))


@admin.register(SeasonCourseOffering)
class SeasonCourseOfferingAdmin(admin.ModelAdmin):
    list_display = ('season', 'course', 'course_price', 'payment_term_days', 'grace_period_days', 'approved', 'registration_open', 'registration_opens_at', 'registration_closes_at', 'waiting_list_enabled')
    list_filter = ('season', 'approved', 'registration_open', 'waiting_list_enabled')
    search_fields = ('season__name', 'course__title')
    list_select_related = ('season', 'course')
    autocomplete_fields = ('course',)
    readonly_fields = ('approved_by', 'approved_at', 'approval_signature')
    fieldsets = (
        ('Cursusaanbod', {'fields': ('season', 'course')}),
        ('Goedkeuring', {'fields': ('approved', 'coverage_override', 'override_reason', 'approved_by', 'approved_at', 'approval_signature')}),
        ('Inschrijving', {'fields': ('registration_open', 'registration_opens_at', 'registration_closes_at', 'waiting_list_enabled')}),
        ('Financiën', {'fields': ('course_price', 'payment_term_days', 'grace_period_days')}),
    )


@admin.register(TrainerSeasonAvailability)
class TrainerSeasonAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('season', 'trainer', 'response', 'updated_at')
    list_filter = ('season', 'response')
    search_fields = ('trainer__username', 'trainer__first_name', 'trainer__last_name', 'season__name')
    list_select_related = ('season', 'trainer')
    readonly_fields = ('updated_at',)


@admin.register(LessonInstructorOverride)
class LessonInstructorOverrideAdmin(admin.ModelAdmin):
    list_display = ('group', 'lesson_date', 'trainer', 'offline_confirmed')
    list_filter = ('offline_confirmed', 'lesson_date', 'group__season')
    search_fields = ('group__name', 'trainer__username')
    list_select_related = ('group', 'trainer')


class PaymentEventInline(admin.TabularInline):
    model = RegistrationPaymentEvent
    extra = 0
    can_delete = False
    fields = (
        'recorded_at', 'action', 'old_status', 'new_status',
        'actor', 'note',
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class StripeCheckoutAttemptInline(admin.TabularInline):
    model = StripeCheckoutAttempt
    extra = 0
    can_delete = False
    fields = (
        'session_id', 'payment_intent_id', 'amount_cents',
        'currency', 'created_at', 'completed_at',
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RegistrationPayment)
class RegistrationPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'reference', 'applicant', 'course', 'season',
        'amount_due', 'status', 'due_at', 'paid_at', 'cancelled_at',
    )
    list_display_links = ('id', 'reference')
    list_filter = ('status', 'application__season', 'application__course')
    search_fields = (
        '=id', 'reference', 'application__email',
        'application__first_name', 'application__last_name',
        'application__dog_name',
    )
    list_select_related = ('application__course', 'application__season')
    readonly_fields = (
        'id', 'application', 'reference', 'amount_due', 'currency',
        'status', 'due_at', 'paid_at', 'reminder_sent_at',
        'grace_notice_sent_at', 'cancelled_at', 'cancellation_reason',
        'paid_by', 'method', 'note', 'created_at', 'updated_at',
    )
    inlines = (PaymentEventInline, StripeCheckoutAttemptInline)
    ordering = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Cursist')
    def applicant(self, obj):
        app = obj.application
        return ' '.join(filter(None, (app.first_name, app.last_name)))

    @admin.display(description='Cursus')
    def course(self, obj):
        return obj.application.course

    @admin.display(description='Seizoen')
    def season(self, obj):
        return obj.application.season
