from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.core.exceptions import ValidationError
from .models import Season, Dog, Combination, TrainingGroup, Enrollment
from .forms import SeasonForm, DogForm, CombinationForm, TrainingGroupForm, EnrollmentForm

def is_planner(user):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists())

@user_passes_test(is_planner, login_url='accounts:login')
def overview(request):
    seasons=Season.objects.annotate(group_count=Count('groups',distinct=True)).all()
    return render(request,'planning/overview.html',{'seasons':seasons,'dogs':Dog.objects.count(),'combinations':Combination.objects.count()})

@user_passes_test(is_planner, login_url='accounts:login')
def season_detail(request, pk):
    season=get_object_or_404(Season,pk=pk)
    groups=TrainingGroup.objects.filter(season=season).select_related('trainer').annotate(placed_count=Count('enrollments',filter=Q(enrollments__status='placed')))
    return render(request,'planning/season_detail.html',{'season':season,'groups':groups})

@user_passes_test(is_planner, login_url='accounts:login')
def group_detail(request,pk):
    group=get_object_or_404(TrainingGroup.objects.select_related('season','trainer'),pk=pk)
    enrollments=group.enrollments.select_related('combination__handler','combination__dog').all()
    return render(request,'planning/group_detail.html',{'group':group,'enrollments':enrollments,'placed_count':enrollments.filter(status='placed').count()})

@user_passes_test(is_planner, login_url='accounts:login')
def records(request,kind):
    config={'dogs':(Dog,'Honden'),'combinations':(Combination,'Combinaties'),'enrollments':(Enrollment,'Inschrijvingen')}
    if kind not in config: raise Http404
    model,title=config[kind]
    queryset=model.objects.all()
    if kind=='combinations': queryset=queryset.select_related('handler','dog')
    if kind=='enrollments': queryset=queryset.select_related('group','combination__handler','combination__dog')
    return render(request,'planning/records.html',{'records':queryset[:250],'kind':kind,'heading':title,'total':queryset.count()})

@user_passes_test(is_planner, login_url='accounts:login')
def edit(request,kind,pk=None):
    config={'seasons':(Season,SeasonForm,'Seizoen'),'groups':(TrainingGroup,TrainingGroupForm,'Lesgroep'),'dogs':(Dog,DogForm,'Hond'),'combinations':(Combination,CombinationForm,'Combinatie'),'enrollments':(Enrollment,EnrollmentForm,'Inschrijving')}
    if kind not in config: raise Http404
    model,form_type,title=config[kind]
    instance=get_object_or_404(model,pk=pk) if pk else None
    form=form_type(request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        record=form.save(commit=False)
        try:
            record.full_clean()
        except ValidationError as error:
            for field, errors in error.message_dict.items():
                for msg in errors: form.add_error(field if field in form.fields else None,msg)
        else:
            record.save()
            messages.success(request,f'{title} opgeslagen.')
            if kind=='seasons': return redirect('planning:season_detail',pk=record.pk)
            if kind=='groups': return redirect('planning:group_detail',pk=record.pk)
            if kind=='enrollments': return redirect('planning:group_detail',pk=record.group_id)
            return redirect('planning:records',kind=kind)
    return render(request,'planning/edit.html',{'form':form,'heading':title,'editing':bool(pk),'kind':kind})

@user_passes_test(is_planner, login_url='accounts:login')
def catalogue(request):
    from apps.website.views import _managed_course_queryset, _can_manage_course
    return render(request, 'planning/catalogue.html', {
        'courses': _managed_course_queryset().order_by('menu_order', 'title'),
        'can_add': _can_manage_course(request.user, 'add'),
        'can_change': _can_manage_course(request.user, 'change'),
    })
