from csv import DictReader
from itertools import groupby
from collections import OrderedDict
from datetime import date, datetime

from io import TextIOWrapper
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.urls import resolve, reverse
from django.utils.translation import gettext as _
from django.utils.dateparse import parse_date
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import never_cache
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings 

from .models import *
from django.utils import timezone
from .utils import (get_timetable_context, get_schedules_table, get_days_periods,
    get_events, get_display_context, get_teacher_by_name)
from .forms import *
from django.contrib.auth import login, authenticate
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from timetable.forms import SignUpForm
from .render import Render
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import View

from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import tempfile
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from weasyprint import default_url_fetcher, HTML
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from weasyprint.fonts import FontConfiguration




def password_reset_request(request):
	if request.method == "POST":
		password_reset_form = PasswordResetForm(request.POST)
		if password_reset_form.is_valid():
			data = password_reset_form.cleaned_data['email']
			associated_users = User.objects.filter(Q(email=data)|Q(username=data))
			if associated_users.exists():
				for user in associated_users:
					subject = "Password Reset Requested"
					email_template_name = "timetable/password/password_reset_email.txt"
					c = {
					"email":user.email,
					'domain':'127.0.0.1:8000',
					'site_name': 'Website',
					"uid": urlsafe_base64_encode(force_bytes(user.pk)).decode(),
					"user": user,
					'token': default_token_generator.make_token(user),
					'protocol': 'http',
					}
					email = render_to_string(email_template_name, c)
					try:
						send_mail(subject, email, 'josenyamos@gmail.com' , [user.email], fail_silently=False)
					except BadHeaderError:
						return HttpResponse('Invalid header found.')
					messages.success(request, 'A message with reset password instructions has been sent to your inbox.')
					return redirect ("timetable:home")
	password_reset_form = PasswordResetForm()
	return render(request=request, template_name='timetable/password/password_reset.html', context={"password_reset_form":password_reset_form})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})



@login_required
@vary_on_cookie
def show_timetable(request):
    """Redirects to timetable given in GET parameter or in cookies"""
    klass = request.GET.get('class')
    if klass:
        return HttpResponseRedirect('/timetable/class/'+klass+'/')

    teacher = request.GET.get('teacher')
    if teacher:
        return HttpResponseRedirect('/timetable/teacher/'+teacher+'/')

    room = request.GET.get('room')
    if room:
        return HttpResponseRedirect('/timetable/room/'+room+'/')

    user_default = request.COOKIES.get('timetable_default') # set in JS
    version = request.COOKIES.get('timetable_version')
    if user_default is None or str(version) != str(settings.TIMETABLE_VERSION):
        response = HttpResponseRedirect('/timetable/class/1/')
        response.delete_cookie('timetable_default', path='/timetable/')
        response.delete_cookie('timetable_version', path='/timetable/')
        return response
    return HttpResponseRedirect(user_default)



def show_class_timetable(request, class_id):
    klass = get_object_or_404(Class, pk=class_id)
    groups = Group.objects.filter(classes=klass)
    lessons = Lesson.objects.filter(group__in=groups)
    today = timezone.now()
    context = get_timetable_context(lessons)
    context['class'] = klass
    context['groups'] = groups
    context['today'] = today
    context['urlname'] = 'timetable/classpdf/'+str(class_id)+'/'
    # context['id'] = class_id
    return render(request, 'class_timetable.html', context)

def class_timetable_pdf(request,class_id):
    """Generate pdf."""
    # Model data
    klass = get_object_or_404(Class, pk=class_id)
    groups = Group.objects.filter(classes=klass)
    lessons = Lesson.objects.filter(group__in=groups)
    today = timezone.now()
    context = get_timetable_context(lessons)
    context['today'] = today
    context['class'] = klass
    context['groups'] = groups
    # context['tt'] = "WEEKLY PROGRAM FOR"+title
    html_string = render_to_string('classpdf.html', context)
    html = HTML(string=html_string)
    html.write_pdf(target="tmp/classpdf.pdf",zoom=6)
    fs = FileSystemStorage("tmp")
    with fs.open('classpdf.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="classpdf.pdf"'
        return response
    return response

def show_groups_timetable(request, group_ids):
    try:
        group_ids = [int(n) for n in group_ids.split(',')]
    except:
        raise Http404
    groups = Group.objects.filter(pk__in=group_ids)
    if len(groups) != len(group_ids):
        raise Http404
    lessons = Lesson.objects.filter(group__in=group_ids)
    context = get_timetable_context(lessons)
    context['groups'] = groups
    return render(request, 'group_timetable.html', context)

def show_room_timetable(request, room_id):
    room = get_object_or_404(Room, pk=room_id)
    lessons = Lesson.objects.filter(room=room).prefetch_related('group__classes')
    context = get_timetable_context(lessons)
    today = timezone.now()
    context['room'] = room
    context['today'] = today
    context['urlname'] = 'timetable/roompdf/'+str(room_id)+'/'
    return render(request, 'room_timetable.html', context)


def room_timetable_pdf(request,room_id):
    """Generate pdf."""
    room = get_object_or_404(Room, pk=room_id)
    lessons = Lesson.objects.filter(room=room).prefetch_related('group__classes')
    context = get_timetable_context(lessons)
    today = timezone.now()
    context['room'] = room
    context['today'] = today
    html_string = render_to_string('roompdf.html', context)
    html = HTML(string=html_string)
    html.write_pdf(target="tmp/roompdf.pdf")
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri())
    fs = FileSystemStorage("tmp")
    with fs.open('roompdf.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="roompdf.pdf"'
        return response
    return response


def show_teacher_timetable(request, teacher_id):
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    lessons = Lesson.objects.filter(teacher=teacher).prefetch_related('group__classes')
    context = get_timetable_context(lessons)
    today = timezone.now()
    context['teacher'] = teacher
    context['today'] = today
    context['timetable_teacher'] = teacher
    context['urlname'] = 'timetable/teacherpdf/'+str(teacher_id)+'/'
    return render(request, 'teacher_timetable.html', context)

def teacher_timetable_pdf(request,teacher_id):
    """Generate pdf."""
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    lessons = Lesson.objects.filter(teacher=teacher).prefetch_related('group__classes')
    context = get_timetable_context(lessons)
    today = timezone.now()
    context['teacher'] = teacher
    context['timetable_teacher'] = teacher
    context['today'] = today
    html_string = render_to_string('teacherpdf.html', context)
    html = HTML(string=html_string)
    html.write_pdf(target="tmp/teacherpdf.pdf")
    fs = FileSystemStorage("tmp")
    with fs.open('teacherpdf.pdf') as pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="teacherpdf.pdf"'
        return response
    return response

def personalize(request, class_id):
    #TODO: switch to a Django form?
    context = dict()
    if request.POST:
        groups = request.POST.getlist('group-checkbox')
        if not groups:
            context['error'] = _('Select at least one group')
        else:
            url = reverse('groups_timetable', args=[','.join(groups)])
            return HttpResponseRedirect(url)
    klass = get_object_or_404(Class, pk=class_id)
    groups = Group.objects.filter(classes=klass)
    context['class'] = klass
    context['groups'] = groups
    return render(request, 'personalization.html', context)

def show_schedules(request):
    context = get_schedules_table()
    return render(request, 'schedules.html', context)

class AddSubstitutionsView1(PermissionRequiredMixin, FormView):
    """The first step to adding a substitution

    selects a teacher and a date to be passed into the second step
    """
    permission_required = 'timetable.add_substitution'
    template_name = 'teacher_and_date_select.html'
    form_class = SelectTeacherAndDateForm

    def form_valid(self, form):
        teacher = form.cleaned_data['teacher']
        date = form.cleaned_data['date']
        return redirect('add_substitutions2', teacher.pk, str(date))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        end_date = date(today.year + 1, today.month, today.day)
        events = get_events(end_date=end_date)
        context['substitutions'] = events['substitutions']
        context['show_substitution_delete'] = True
        return context

@never_cache
@login_required
@permission_required('timetable.add_substitution', raise_exception=True)
def add_substitutions2(request, teacher_id, date):
    date = parse_date(date)
    teacher = get_object_or_404(Teacher, pk=teacher_id)

    if request.method == 'POST':
        formset = SubstitutionFormSet(teacher, date, request.POST)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(reverse('add_substitutions1'))
    else:
        formset = SubstitutionFormSet(teacher, date)

    context = {
        'teacher': teacher,
        'formset': formset,
        'date': date,
    }
    return render(request, 'add_substitutions.html', context)

@never_cache
@login_required
@permission_required('timetable.add_dayplan', raise_exception=True)
def edit_calendar(request):
    qs = DayPlan.objects.filter(date__gte=date.today())
    if request.method == 'POST':
        formset = DayPlanFormSet(request.POST, queryset=qs)
        if formset.is_valid():
            formset.save()
            # Refresh the formset by refreshing the page
            return HttpResponseRedirect(request.path)
    else:
        formset = DayPlanFormSet(queryset=qs)
    context = {'formset': formset}
    return render(request, 'edit_calendar.html', context)

def show_rooms(request, date, period):
    date = parse_date(date)
    weekday = date.weekday()
    period = int(period)

    rooms = {room: None for room in Room.objects.all()}
    lessons = Lesson.objects.filter(weekday=weekday, period=period) \
        .select_related('room', 'teacher', 'group', 'subject')
    for lesson in lessons:
        rooms[lesson.room] = lesson

    substitutions = Substitution.objects.filter(date=date, lesson__period=period)
    for sub in substitutions:
        rooms[sub.lesson.room].substitute = sub.substitute

    context = {
        'date': date,
        'period': period,
        'rooms': rooms,
    }
    return render(request, 'rooms.html', context)

class RoomsDatePeriodSelectView(FormView):
    """A form with date and period to be passed to show_rooms."""
    template_name = 'rooms_date_period_select.html'
    form_class = SelectDateAndPeriodForm

    def form_valid(self, form):
        date = form.cleaned_data['date']
        period = form.cleaned_data['period']
        return redirect('rooms', date, period)

@never_cache
def display(request):
    context = get_display_context()
    return render(request, 'display.html', context)


# This is view that should expose DayPlan, Schedule and Period models
# in JSON format for use in automated bell system.
# It should be incorporated in zorza API if one would be implemented
@never_cache
def timetable_bell_api(request):

    days = settings.BELL_API_TIMESPAN

    if not days > 0:
        raise Http404()

    now = datetime.datetime.now()

    #make dictionary
    data = {}
    data['date'] = { 'year': now.year, 'month': now.month, 'day': now.day }
    data['time'] = { 'hour': now.hour, 'minute': now.minute, 'second': now.second }
    data['bells'] = []

    current_date = now.date()
    for a in range(days):
        times = []
        for t in get_days_periods(current_date):
            times.append([t.begin_time.hour,t.begin_time.minute])
            times.append([t.end_time.hour,t.end_time.minute])
        times.sort()
        data['bells'].append(times)
        current_date += datetime.timedelta(days=1)

    return JsonResponse(data)

@login_required
@permission_required('timetable.add_substitution', raise_exception=True)
def delete_substitution(request, substitution_id):
    if request.POST:
        obj = get_object_or_404(Substitution, pk=substitution_id)
        obj.delete()
        return HttpResponseRedirect(reverse('add_substitutions1'))

class SubstitutionsImportView(FormView):
    template_name = 'import_substitutions.html'
    form_class = SubstitutionsImportForm
    permission_required = 'timetable.add_substitution'

    def form_valid(self,form):
        csv_file = TextIOWrapper(
            form.cleaned_data['file'],
            encoding=settings.TIMETABLE_CSV_ENCODING)
        reader = DictReader(
            csv_file, skipinitialspace=True,
            delimiter=settings.TIMETABLE_CSV_DELIMITER)
        HEADER = settings.TIMETABLE_CSV_HEADER
        context = {
            'rows_failed': 0,
            'rows_added': 0,
            'rows_updated': 0,
            'substitutions': [],
            'errors': [],
        }
        for row in reader:
            try:
                #sub_date = parse_date(row[HEADER['date']])
                sub_date = parse_date(row[HEADER['date']].split()[0])
                tname = row[HEADER['teacher']]
                teacher = (get_teacher_by_name(tname, False) or
                        get_teacher_by_name(tname, True))
                lesson = Lesson.objects.get(
                        weekday=sub_date.weekday(),
                        period=int(row[HEADER['period']]),
                        teacher=teacher)
                sname = row[HEADER['substitute']]
                substitute = (get_teacher_by_name(sname, False) or
                        get_teacher_by_name(sname, True))

                obj, created = Substitution.objects.update_or_create(
                        date=sub_date, lesson=lesson,
                        defaults={'substitute': substitute})
                context['substitutions'].append(obj)
                if created:
                    context['rows_added'] += 1
                else:
                    context['rows_updated'] += 1
            except Exception as e:
                if ''.join(filter(None, row.values())) == '':
                    # Blank line
                    continue
                context['rows_failed'] += 1
                context['errors'].append(row)
        return render(self.request, 'csv_import_success.html', context)
