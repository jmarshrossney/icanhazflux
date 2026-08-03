from datetime import UTC, datetime

from icanhazflux.objects import build_time_filters, parse_time


def test_parse_time_none():
    assert parse_time(None) is None


def test_parse_time_datetime_passthrough():
    dt = datetime(2024, 6, 1, tzinfo=UTC)
    assert parse_time(dt) is dt


def test_parse_time_date_start_of_day():
    assert parse_time("2024-06-01") == "2024-06-01T00:00:00Z"


def test_parse_time_date_end_of_day():
    assert parse_time("2024-06-01", end_of_day=True) == "2024-06-01T23:59:59Z"


def test_parse_time_full_iso_unchanged():
    assert parse_time("2024-06-01T12:30:00Z") == "2024-06-01T12:30:00Z"


def test_build_time_filters_empty():
    assert build_time_filters() == []


def test_build_time_filters_start_only():
    filters = build_time_filters(start="2024-06-01")
    assert len(filters) == 1
    f = filters[0]
    assert f.prop == "timeEnd"
    assert f.op == ">"
    assert f.value == "2024-06-01T00:00:00Z"


def test_build_time_filters_end_only():
    filters = build_time_filters(end="2024-06-03")
    assert len(filters) == 1
    f = filters[0]
    assert f.prop == "timeStart"
    assert f.op == "<"
    assert f.value == "2024-06-03T23:59:59Z"


def test_build_time_filters_range_overlap_semantics():
    filters = build_time_filters(start="2024-06-01", end="2024-06-03")
    assert len(filters) == 2
    by_prop = {f.prop: f for f in filters}
    assert by_prop["timeEnd"].op == ">"
    assert by_prop["timeEnd"].value == "2024-06-01T00:00:00Z"
    assert by_prop["timeStart"].op == "<"
    assert by_prop["timeStart"].value == "2024-06-03T23:59:59Z"
