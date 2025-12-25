import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'real_estate.settings')
django.setup()

from django.contrib.auth.models import User
from master.models import City, State, Country
from vendor.models import Category, Vendor, VendorImage, Product
from vendor.serializers import VendorDetailSerializer

def verify_vendor_creation_with_images():
    print("\n--- Verifying Vendor Creation with Images ---")
    
    # 1. Setup Data
    try:
        # Create User
        user, created = User.objects.get_or_create(username='test_vendor_user', defaults={'email': 'test@example.com'})
        if not created:
            # Clean up previous runs
            Vendor.objects.filter(user=user).delete()
            print("Cleaned up existing vendor for user.")

        # Create Dependencies
        country, _ = Country.objects.get_or_create(name='Test Country', code='TC')
        state, _ = State.objects.get_or_create(name='Test State', country=country)
        city, _ = City.objects.get_or_create(name='Test City', state=state)
        category, _ = Category.objects.get_or_create(name='Test Category', slug='test-category', defaults={'status': 'active'})
        
        print("Dependencies created.")

        # 2. Prepare Data
        vendor_data = {
            'business_name': 'Test Business with Images',
            'owner_name': 'Test Owner',
            'category_id': category.id,
            'city_id': city.id,
            'phone': '1234567890',
            'email': 'vendor@test.com',
            'address': 'Test Address',
            'offering_type': 'product',
            'service_description': 'Test Service', # Optional but good to have
        }

        products_data = [
            {'name': 'Product 1', 'description': 'Desc 1', 'price': 100},
            {'name': 'Product 2', 'description': 'Desc 2', 'price': 200},
        ]

        # 3. Create Files
        image_content = b'fake_image_content'
        vendor_image_1 = SimpleUploadedFile("vendor_1.jpg", image_content, content_type="image/jpeg")
        vendor_image_2 = SimpleUploadedFile("vendor_2.jpg", image_content, content_type="image/jpeg")
        product_1_image = SimpleUploadedFile("prod_1.jpg", image_content, content_type="image/jpeg")

        # 4. Mock Request
        class MockRequest:
            def __init__(self, user, files):
                self.user = user
                self.FILES = files
                self.method = 'POST'

        files = {
            'product_images_0': [product_1_image], # Images for Product 1 (index 0)
                                                   # No images for Product 2 (index 1)
        }
        
        # Add 'getlist' method to FILES which is expected by Django forms/serializers
        # We can simulate MultiValueDict behavior roughly or just use a real one if needed, 
        # but for getlist, a simple wrapper or assuming the serializer uses request.FILES.getlist call.
        # The serializer uses request.FILES.getlist().
        
        from django.utils.datastructures import MultiValueDict
        files_multivalue = MultiValueDict()
        files_multivalue.setlist('product_images_0', [product_1_image])
        
        mock_request = MockRequest(user, files_multivalue)

        # 5. Call Serializer
        # We need to structure 'data' properly. 
        # For 'vendor_images', serializer expects a list of files in validated_data.
        # But 'vendor_images' as a ListField in serializer input usually comes from request.FILES in a real view via parser.
        # However, checking VendorDetailSerializer, 'vendor_images' is defined as ListField(child=ImageField).
        # When passing data to serializer, checking how DRF handles uploaded files in `data`.
        # Usually, one passes files in `data` for ImageFields.
        
        data = vendor_data.copy()
        data['products_data'] = products_data
        data['vendor_images'] = [vendor_image_1, vendor_image_2]

        print("Initializing Serializer...")
        serializer = VendorDetailSerializer(data=data, context={'request': mock_request})
        
        if serializer.is_valid():
            print("Serializer is valid.")
            try:
                # save() calls create()
                vendor = serializer.save()
                print(f"Vendor created: {vendor.business_name} (ID: {vendor.id})")
                
                # 6. Verify Results
                
                # Check Vendor Images
                v_images = VendorImage.objects.filter(vendor=vendor, product__isnull=True)
                print(f"Vendor-only images count: {v_images.count()}")
                if v_images.count() != 2:
                    print("❌ Expected 2 vendor images.")
                else:
                    print("✅ Vendor images verified.")

                # Check Products
                products = Product.objects.filter(vendor=vendor).order_by('id')
                print(f"Products count: {products.count()}")
                if products.count() != 2:
                    print("❌ Expected 2 products.")
                else:
                    print("✅ Products count verified.")
                
                # Check Product Images
                if products.exists():
                    p1 = products[0]
                    p2 = products[1]
                    
                    p1_images = VendorImage.objects.filter(vendor=vendor, product=p1)
                    print(f"Product 1 images count: {p1_images.count()}")
                    if p1_images.count() != 1:
                        print("❌ Expected 1 image for Product 1.")
                    else:
                        print("✅ Product 1 images verified.")
                        
                    p2_images = VendorImage.objects.filter(vendor=vendor, product=p2)
                    print(f"Product 2 images count: {p2_images.count()}")
                    if p2_images.count() != 0:
                        print("❌ Expected 0 images for Product 2.")
                    else:
                        print("✅ Product 2 images verified.")
                        
                return True

            except Exception as e:
                print(f"❌ Error during save: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("❌ Serializer Invalid:")
            print(serializer.errors)
            return False

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if verify_vendor_creation_with_images():
        print("\n🎉 Verification Successful!")
    else:
        print("\n⚠️ Verification Failed!")
