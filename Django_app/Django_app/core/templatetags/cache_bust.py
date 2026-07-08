"""Appends the static file's last-modified time as a cache-busting query
string, so browsers pick up CSS/JS edits during dev without a hard
refresh, without needing collectstatic/ManifestStaticFilesStorage.
"""

import os

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def cbstatic(path):
    url = static(path)
    for static_dir in settings.STATICFILES_DIRS:
        full_path = os.path.join(static_dir, path)
        if os.path.exists(full_path):
            return f"{url}?v={int(os.path.getmtime(full_path))}"
    return url
