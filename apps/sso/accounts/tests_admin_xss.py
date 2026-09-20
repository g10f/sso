from django.contrib.auth import get_user_model
from django.test import TestCase

from sso.accounts.admin import UserNoteAdmin
from sso.accounts.models import Application, UserNote
from sso.admin import sso_admin_site
from sso.organisations.models import Organisation

XSS = '<script>alert(1)</script>'


class AdminXssTest(TestCase):
    """
    Regression tests for the stored XSS that was possible because admin/model
    methods built HTML with mark_safe and %-formatting of user-controlled data.
    They now use format_html, which escapes the interpolated values.
    """

    def test_admin_user_link_escapes_username(self):
        # a username with html can be stored via the self-registration path,
        # where the model validator does not run
        user = get_user_model().objects.create(username=XSS)
        note = UserNote(user=user)
        html = str(UserNoteAdmin(UserNote, sso_admin_site).user_link(note))
        self.assertNotIn(XSS, html)
        self.assertIn('&lt;script&gt;', html)

    def test_application_link_escapes_url(self):
        html = str(Application(url='http://x/">%s' % XSS).link())
        self.assertNotIn(XSS, html)

    def test_organisation_homepage_link_escapes(self):
        org = Organisation(homepage='http://x/">%s' % XSS, association=None)
        html = str(org.homepage_link())
        self.assertNotIn(XSS, html)
