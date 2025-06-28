import csv
import dataclasses
from datetime import date
from io import StringIO

from dateutil.relativedelta import relativedelta
from dateutil.rrule import *
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse

from main.test.test_permissions_helpers import no_perms_test
from reporting.matomo import usage

from .admin.usage_dashboard import DateForm


def sql_to_csv_response(sql: str, filename: str) -> HttpResponse:
    """Given a blob of SQL, execute it, set the row headers to the column names, and return a downloadable CSV"""

    with connection.cursor() as cursor:
        cursor.execute(sql)
        output = StringIO()
        export = []
        export.append([col.name.replace("_", " ") for col in cursor.description])
        export.extend(cursor.fetchall())
        csv.writer(output).writerows(export)

        return HttpResponse(
            output.getvalue().encode(),
            headers={
                "Content-Type": "text/csv",
                "Content-Disposition": f'attachment; filename="{filename}-{date.today().isoformat()}.csv"',
            },
        )


@no_perms_test
@staff_member_required
def matomo_stats(request: HttpRequest) -> JsonResponse:
    """When requested as on page load, retrieve Matomo analytics for the given time period"""
    form = DateForm(request.GET)
    if form.is_valid():
        web_usage = usage(
            form.cleaned_data["start_date"],
            form.cleaned_data["end_date"],
            form.cleaned_data["published"],
        )
        return JsonResponse(dataclasses.asdict(web_usage))
    return JsonResponse("")


@no_perms_test
@staff_member_required
def professor_cumulative_publication_timeseries(request: HttpRequest) -> HttpResponse:
    """Cumulative casebooks published by verified professors"""

    sql = """--sql
        select 
            published_year::text as "Year", 
            sum(count(user_id)) over (order by published_year) as "Casebooks by professors"
        from reporting_professors_with_casebooks_over_time 
        group by published_year
        """
    return sql_to_csv_response(sql, "professor-casebooks-published-over-time")


@no_perms_test
@staff_member_required
def professor_casebook_timeseries(request: HttpRequest) -> HttpResponse:
    """Cumulative casebooks published by verified professors"""

    # These do not respect date filters because they're cumulative over all time
    year_qs = []
    for year in rrule(YEARLY, until=date.today(), dtstart=date.today() - relativedelta(years=10)):
        year_qs.append(
            f'case when created_year = {year.year} then num_casebooks else 0 end as "year_{year.year}"\n'
        )
    sql = f"""--sql
        select distinct user_id, attribution,
        {', '.join([yq for yq in year_qs])}
        from reporting_professors_with_casebooks_over_time
        """
    return sql_to_csv_response(sql, "professor-casebooks-published-over-time")


@no_perms_test
@staff_member_required
def casebook_timeseries(request: HttpRequest) -> HttpResponse:
    """Casebooks by verified professors that were published in the given year"""
    sql = """--sql

    with ever_published as (
        select distinct casebook_id, entry_date from main_casebookeditlog 
        where change = 'First'
    ) -- edit log was backfilled 

    select 
        extract(year from log.entry_date)::text as Year, 
        count(c.casebook_id) as "Casebook count"
    from reporting_casebooks_from_professors c
    inner join ever_published log 
        on log.casebook_id = c.casebook_id
    group by extract(year from log.entry_date)
    order by year
    """

    return sql_to_csv_response(sql, "casebooks-published-over-time")
