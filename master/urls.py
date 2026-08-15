from django.urls import path
from django.contrib.sitemaps.views import sitemap
from .views import HomeView, AboutView, IndustriesView, ServicesView, ProductsView, TechnologiesView, PortfolioView, ContactView, PrivacyPolicyView, RobotsTxtView, LLMTxtView, SitemapView, submit_contact_form
from .sitemaps import StaticViewSitemap

app_name = 'master'

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('industries/', IndustriesView.as_view(), name='industries'),
    path('services/', ServicesView.as_view(), name='services'),
    path('products/', ProductsView.as_view(), name='products'),
    path('technologies/', TechnologiesView.as_view(), name='technologies'),
    path('portfolio/', PortfolioView.as_view(), name='portfolio'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('sitemap/', SitemapView.as_view(), name='sitemap'),
    path('api/contact/submit/', submit_contact_form, name='api_contact_submit'),
    path('robots.txt', RobotsTxtView.as_view(), name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap_xml'),
    # Error Page Previews
    path('404/', HomeView.as_view(template_name='404.html'), name='preview_404'),
    path('500/', HomeView.as_view(template_name='500.html'), name='preview_500'),
]
