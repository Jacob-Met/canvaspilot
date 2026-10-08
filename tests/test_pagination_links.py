"""Protocol edge cases separate from the receiving client/HTTP tests."""

import pytest

from canvaspilot.pagination import CanvasPaginationError, broker_path, next_link


def test_documented_canvas_link_header():
    header = ', '.join([
        '<https://school.instructure.com/api/v1/courses?opaqueA>; rel="current"',
        '<https://school.instructure.com/api/v1/courses?opaqueB>; rel="next"',
        '<https://school.instructure.com/api/v1/courses?opaqueC>; rel="first"',
        '<https://school.instructure.com/api/v1/courses?opaqueD>; rel="last"',
    ])
    assert next_link(header) == "https://school.instructure.com/api/v1/courses?opaqueB"


def test_quoted_delimiters_and_relation_text_inside_title_are_not_links():
    header = '<https://school.instructure.com/a?cursor=1,2>; title="; rel=next, <text>"; rel="prev"'
    assert next_link(header) is None


def test_next_is_an_exact_relation_and_can_be_in_a_relation_list():
    assert next_link('<https://school.instructure.com/no>; rel="nextish"') is None
    assert next_link('<https://school.instructure.com/yes>; ReL="prev next"') == 'https://school.instructure.com/yes'
    assert next_link('<https://school.instructure.com/yes>; rel=next') == 'https://school.instructure.com/yes'


@pytest.mark.parametrize("header", [
    '<https://school.instructure.com/a>; rel="next", <https://school.instructure.com/b>; rel=next',
    '<https://school.instructure.com/a>; rel="next"; rel="prev"',
    '<https://school.instructure.com/a>; rel="next',
    '<https://school.instructure.com/a; rel="next"',
    'https://school.instructure.com/a; rel="next"',
    '<https://school.instructure.com/a>; rel=""',
])
def test_malformed_or_ambiguous_link_header_is_not_silently_terminal(header):
    with pytest.raises(CanvasPaginationError):
        next_link(header)


def test_same_origin_url_is_made_relative_without_decoding_query():
    url = 'https://SCHOOL.instructure.com:443/api/v1/courses?after=a%2Fb%2Bc&filter[]=one&filter[]=two'
    assert broker_path(url, 'https://school.instructure.com') == (
        '/api/v1/courses?after=a%2Fb%2Bc&filter[]=one&filter[]=two'
    )
    assert broker_path('/api/v1/courses?cursor=next', 'https://school.instructure.com') == (
        '/api/v1/courses?cursor=next'
    )
