from uritemplate import expand

from django.core.paginator import Paginator
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from sso.accounts.models import User, UserEmail
from sso.api.views.generic import DistinctPkPaginator
from sso.oauth2.tests import OAuth2BaseTestCase


class DistinctPkPaginatorTests(OAuth2BaseTestCase):
    def setUp(self):
        super().setUp()
        UserEmail.objects.create(user=User.objects.get(username='GlobalAdmin'), email='second-address@g10f.de')

    def joined_distinct_queryset(self):
        return User.objects.filter(useremail__email__icontains='@g10f.de').distinct().order_by('username')

    def test_count_matches_default_paginator_for_queryset_with_duplicate_joins(self):
        qs = self.joined_distinct_queryset()
        joined_rows = User.objects.filter(useremail__email__icontains='@g10f.de').count()
        self.assertGreater(joined_rows, qs.count())

        self.assertEqual(DistinctPkPaginator(qs, 2).count, Paginator(qs, 2).count)

    def test_count_query_selects_primary_key_only(self):
        with CaptureQueriesContext(connection) as queries:
            DistinctPkPaginator(self.joined_distinct_queryset(), 2).count

        self.assertEqual(len(queries), 1)
        sql = queries[0]['sql']
        self.assertIn('DISTINCT', sql)
        self.assertNotIn('"accounts_user"."password"', sql)
        self.assertNotIn('ORDER BY', sql)

    def test_user_list_out_of_range_page_counts_primary_keys_only(self):
        users_url = expand(self.client.get(reverse('api:home')).json()['users'])
        authorization = self.get_authorization(client_id="1811f02ed81b43b5bee1afe031e6198e",
                                               username="CountryAdmin", scope="users")

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(users_url, {'page': 999999, 'per_page': 2},
                                       HTTP_AUTHORIZATION=authorization)

        self.assertEqual(response.status_code, 404)
        count_queries = [query['sql'] for query in queries if 'COUNT(' in query['sql']]
        self.assertTrue(count_queries)
        for sql in count_queries:
            self.assertNotIn('"accounts_user"."password"', sql)
