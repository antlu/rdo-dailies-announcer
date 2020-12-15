from datetime import date, datetime, time, timedelta


def current_day_from_iso(iso_date):
    return date.fromisoformat(iso_date).strftime('%B %d')  # noqa: WPS323


def seconds_for_next_update():
    update_time = time(6, second=30)  # noqa: WPS432
    now = datetime.utcnow()
    today_6GMT = datetime.combine(now.date(), update_time)  # noqa: N806,WPS114
    if now <= today_6GMT:
        return (today_6GMT - now).seconds
    tommorow_6GMT = datetime.combine(  # noqa: N806,WPS114
        now.date() + timedelta(days=1),
        update_time,
    )
    return (tommorow_6GMT - now).seconds
