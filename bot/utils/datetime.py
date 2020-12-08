from datetime import date, datetime, time, timedelta


def current_day():
    return datetime.utcnow().strftime('%B %d')  # noqa: WPS323


def seconds_for_next_update():
    tommorow_6GMT = datetime.combine(  # noqa: N806,WPS114
        date.today() + timedelta(days=1),
        time(6, second=30),  # noqa: WPS432
    )
    delta = tommorow_6GMT - datetime.utcnow()
    return delta.seconds
