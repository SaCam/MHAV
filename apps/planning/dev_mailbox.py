"""Inspect test emails. Route exists only with DEBUG enabled."""
from email import policy
from email.parser import BytesParser
from pathlib import Path
import re
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404
from django.shortcuts import render
from .views import is_planner

@user_passes_test(is_planner, login_url='accounts:login')
def mailbox(request):
    if not settings.DEBUG or settings.EMAIL_BACKEND != 'django.core.mail.backends.filebased.EmailBackend':
        raise Http404
    folder = Path(settings.EMAIL_FILE_PATH)
    messages = []
    for file in sorted(folder.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True)[:60]:
        if not file.is_file():
            continue
        raw = file.read_bytes()
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        body = parsed.get_body(preferencelist=('plain',))
        content = body.get_content() if body else ''
        # Link targets must be produced by the local app, never arbitrary external URLs.
        links = [url for url in re.findall(r'https?://[^\s<>]+', content)
                 if url.startswith(request.build_absolute_uri('/'))]
        messages.append({'subject': str(parsed.get('Subject','')),
                         'recipient': str(parsed.get('To','')), 'body': content,
                         'links': links, 'filename': file.name})
    return render(request, 'planning/dev_mailbox.html', {'emails': messages})
