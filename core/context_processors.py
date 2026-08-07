"""
    Context processor to inject SEO metadata from seo.json into templates.
    seo.json is parsed once and cached at module level for the process lifetime.
"""

import json
import os
from django.conf import settings

# Module-level cache — populated once on first request, reused for all subsequent ones.
_SEO_DATA_CACHE = None

def _load_seo_data():
    """Load and cache seo.json from disk. Returns an empty dict on any failure."""
    global _SEO_DATA_CACHE
    if _SEO_DATA_CACHE is not None:
        return _SEO_DATA_CACHE
    seo_file_path = os.path.join(settings.BASE_DIR, 'seo.json')
    try:
        with open(seo_file_path, 'r', encoding='utf-8') as f:
            _SEO_DATA_CACHE = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        _SEO_DATA_CACHE = {}
    return _SEO_DATA_CACHE

def seo_metadata(request):
    path = request.path_info
    if path in ('/robots.txt', '/sitemap.xml'):
        return {}

    seo_data = _load_seo_data()

    # Get metadata for current path, fallback to default
    metadata = seo_data.get(path, seo_data.get('default', {}))

    return {
        'seo_title': metadata.get('title', ''),
        'seo_description': metadata.get('description', ''),
        'seo_keywords': metadata.get('keywords', ''),
        'seo_og_title': metadata.get('og_title', ''),
        'seo_og_description': metadata.get('og_description', ''),
        'seo_twitter_title': metadata.get('twitter_title', ''),
        'seo_twitter_description': metadata.get('twitter_description', ''),
    }
