from datetime import datetime
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    """
    Sitemap for static pages. Generates <lastmod> dynamically using current timestamp.
    """
    priority_dict = {
        'master:home': (1.0, 'weekly'),
        'master:services': (0.9, 'weekly'),
        'master:products': (0.9, 'weekly'),
        'master:industries': (0.9, 'weekly'),
        'master:technologies': (0.9, 'weekly'),
        'master:portfolio': (0.8, 'monthly'),
        'master:about': (0.8, 'monthly'),
        'master:contact': (0.8, 'monthly'),
        'master:privacy_policy': (0.5, 'yearly'),
        'master:sitemap': (0.6, 'monthly'),
    }

    def items(self):
        return list(self.priority_dict.keys())

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return self.priority_dict[item][0]

    def changefreq(self, item):
        return self.priority_dict[item][1]

    def lastmod(self, item):
        return datetime.now()
