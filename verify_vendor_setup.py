import os
import django
from django.conf import settings
from django.urls import resolve, reverse
from django.contrib import admin

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')
django.setup()

from vendor.models import (
    Category, Vendor, VendorImage, Product, Rating, Enquiry,
    VendorCertification, VendorAward
)

def verify_admin_registration():
    print("\nVerifying Admin Registration...")
    models = [
        Category, Vendor, VendorImage, Product, Rating, Enquiry,
        VendorCertification, VendorAward
    ]
    registered = True
    for model in models:
        if not admin.site.is_registered(model):
            print(f"❌ {model.__name__} is NOT registered in admin.")
            registered = False
        else:
            print(f"✅ {model.__name__} is registered in admin.")
    return registered

def verify_urls():
    print("\nVerifying URL Configuration...")
    url_tests = [
        ('category-list', '/api/vendor/categories/', {}),
        ('category-detail', '/api/vendor/categories/1/', {'pk': 1}),
        ('vendor-list', '/api/vendor/vendors/', {}),
        ('vendor-stats', '/api/vendor/vendors/stats/', {}),  # Access directly
        ('vendor-image-list', '/api/vendor/vendors/1/images/', {'vendor_id': 1}),
        ('vendor-product-list', '/api/vendor/vendors/1/products/', {'vendor_id': 1}),
        ('vendor-rating-list', '/api/vendor/vendors/1/ratings/', {'vendor_id': 1}),
        ('vendor-enquiry-create', '/api/vendor/vendors/1/enquire/', {'vendor_id': 1}),
    ]
    
    # We might need to adjust paths based on how vendor.urls is included in main urls
    # Assuming 'api/vendor/' prefix based on common practice or checking main urls if needed.
    # But wait, I don't know the main url includes. 
    # Let's try to resolve by view name to see if it works.
    
    success = True
    try:
        # Check specific important reverse lookups
        stats_url = reverse('vendor-stats')
        print(f"'vendor-stats' resolved to: {stats_url}")
        if 'search' in stats_url:
             print(f"'vendor-stats' still has 'search' in path!")
             success = False
        
        # Check that we can resolve
        for name, _, kwargs in url_tests:
            try:
                path = reverse(name, kwargs=kwargs)
                print(f"Reversed '{name}' to {path}")
            except Exception as e:
                print(f"Could not reverse '{name}': {e}")
                success = False

    except Exception as e:
        print(f"URL Verification failed with error: {e}")
        success = False
        
    return success


if __name__ == "__main__":
    admin_ok = verify_admin_registration()
    urls_ok = verify_urls()
    
    if admin_ok and urls_ok:
        print("\n🎉 Verification Successful!")
    else:
        print("\n⚠️ Verification Failed!")
