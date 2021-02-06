from django_cron import CronJobBase, Schedule
import smtplib
from django.contrib.auth.models import User
import datetime
from notifications.signals import notify
from celery.task import periodic_task
from celery.schedules import crontab
import json
import timetable_create as tc
from django.db.models import Q
from . models import TimeTable, UserProfile


@periodic_task(run_every=crontab(minute=5))
def email_notification_function():
    detail_dict = {}
    user_details = {}
    if datetime.datetime.now() == datetime.datetime.now().replace(hour=8, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period1!='Free' AND DateToday=%s",
                                                [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period1
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "1st period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=9, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period2!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period2
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "2nd period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=10, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period3!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period3
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "3rd period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=12, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period4!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period4
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "4th period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=13, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period5!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period5
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "5th period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=14, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period6!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period6
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "6th period")

    elif datetime.datetime.now() == datetime.datetime.now().replace(hour=15, minute=50, second=0, microsecond=0):
        detail_dict.clear()
        user_details.clear()
        query_rows = list(
            TimeTable.objects.raw("Select * from timetable_timetable WHERE Period7!='Free' AND DateToday=%s",
                                  [datetime.date.today()]))
        for row in query_rows:
            detail_dict["Class"] = row.Period7
            user_details[str(row.user)] = detail_dict
            detail_dict = {}

        send_email(user_details)
        send_notification(user_details, "7th period")


def send_email(user_details):

    for user, value in user_details.iteritems():
        user_details[user]["Email"] = User.objects.get(username=user).email

        timenow = datetime.datetime.now()+ datetime.timedelta(minutes =10)

        FROM = 'elawomenassignment@gmail.com'
        TO = user_details[user]["Email"]


        SUBJECT = "Next Class Details"
        TEXT = "Hello %s! \nYour next class is at the %s standard at %s, and it starts in 10 mins! " \
               "\nPlease be on time. \nRegards \nManagement"\
               % (user, user_details[user]["Class"], timenow.strftime("%X"))

        # Prepare actual message
        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
                """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login('elawomenassignment@gmail.com', 'DifficultPassword')
        server.sendmail(FROM, TO, message)
        server.close()


def send_notification(user_details,period_info):
    username_list = user_details.keys()

    for user in username_list:
        message = "Your "+period_info+" is in "+user_details[user]["Class"]+" standard."
        notify.send(user, recipient=User.objects.get(username=user), verb=message)


@periodic_task(run_every=crontab(minute=0, hour='0'))
def update_profile():
        user_list = []
        for user in User.objects.all():
            user_list.append(User.objects.get(username= str(user)))
        result = []
        for user_instance in user_list:
            result.append(json.loads(str(UserProfile.objects.get(user=user_instance))))

        result_dict = {}

        for d in result:
            for k, v in d.iteritems():
                result_dict.setdefault(k, []).append(v)

        for user in user_list:
            if len(TimeTable.objects.filter(Q(DateToday__gte=datetime.date.today()) &
                                            Q(DateToday__lte=datetime.date.today() + datetime.timedelta(days=3))
                                            ).filter(user=user)) == 0:
                for day in range(0,4):
                    for k, v in result_dict.iteritems():
                        result_dict[k][0]["Class Taken"] = []
                        result_dict[k][0]["Class Timings Today"] = []
                    newRoaster = tc.createTimeTableJson(result_dict, 7, 5)
                    TimeTable.objects.create(user=user,
                                             DateToday=str(datetime.date.today()+ datetime.timedelta(days=day)),
                                             Period1=newRoaster[user.username]["Class Taken"][0],
                                             Period2=newRoaster[user.username]["Class Taken"][1],
                                             Period3=newRoaster[user.username]["Class Taken"][2],
                                             Period4=newRoaster[user.username]["Class Taken"][3],
                                             Period5=newRoaster[user.username]["Class Taken"][4],
                                             Period6=newRoaster[user.username]["Class Taken"][5],
                                             Period7=newRoaster[user.username]["Class Taken"][6])


    