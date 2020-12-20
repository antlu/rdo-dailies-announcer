import time
from datetime import date, datetime, time as dt_time, timedelta

UPDATE_TIME = dt_time(6, second=30)  # noqa: WPS432


def day_from_iso(iso_date):
    month_day = date.fromisoformat(iso_date).strftime('%B %d')  # noqa: WPS323
    month, day = month_day.split()
    return '{0} {1}'.format(_(month), day)


def hm_from_seconds(secs):
    return time.strftime('%Hh %Mm', time.gmtime(secs))


def is_before_update_time():  # noqa: N802,WPS114
    return datetime.utcnow().time() < UPDATE_TIME


def seconds_for_next_update():
    now = datetime.utcnow()
    today_6GMT = datetime.combine(now.date(), UPDATE_TIME)  # noqa: N806,WPS114
    if now <= today_6GMT:
        return (today_6GMT - now).seconds
    tommorow_6GMT = datetime.combine(  # noqa: N806,WPS114
        now.date() + timedelta(days=1),
        UPDATE_TIME,
    )
    return (tommorow_6GMT - now).seconds
