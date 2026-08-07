"""
Middleware to add X-Robots-Tag: noindex, nofollow to all HTTP responses.
This prevents search engines from indexing any page on the site.
Remove or disable this middleware when the site is ready to go live.
"""


class NoIndexMiddleware:
    """Adds X-Robots-Tag: noindex, nofollow header to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
