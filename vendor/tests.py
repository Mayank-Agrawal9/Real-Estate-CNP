from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from master.models import City, State, Country
from vendor.models import Vendor, Category, Product, VendorImage

class VendorImageUploadTests(APITestCase):
    def setUp(self):
        # Create hierarchy for City
        self.country = Country.objects.create(name='India', code='IN')
        self.state = State.objects.create(name='Delhi', country=self.country)
        self.city = City.objects.create(name='New Delhi', state=self.state)

        # Create Category
        self.category = Category.objects.create(name='Electronics', slug='electronics')

        # Create User
        self.user = User.objects.create_user(username='vendor_user', password='password123')

        # Create Vendor
        self.vendor = Vendor.objects.create(
            user=self.user,
            business_name='Tech World',
            owner_name='John Doe',
            category=self.category,
            city=self.city,
            phone='1234567890',
            email='tech@example.com',
            address='123 Tech Park',
            offering_type='product'
        )

        # Create Product
        self.product = Product.objects.create(
            vendor=self.vendor,
            name='Laptop',
            description='Gaming Laptop',
            price=100000.00
        )

        self.client.force_authenticate(user=self.user)
        self.url = reverse('vendorimage-upload-images')  # Assuming basename is vendorimage

    def test_upload_multiple_images(self):
        image1 = SimpleUploadedFile("image1.jpg", b"file_content", content_type="image/jpeg")
        image2 = SimpleUploadedFile("image2.jpg", b"file_content", content_type="image/jpeg")

        data = {
            'vendor': self.vendor.id,
            'product': self.product.id,
            'images': [image1, image2],
            'image_type': 'gallery',
            'caption': 'Test Image',
            'is_primary': False
        }

        # Use format='multipart' for file uploads
        response = self.client.post(self.url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VendorImage.objects.count(), 2)
        
        vendor_images = VendorImage.objects.filter(vendor=self.vendor)
        self.assertEqual(vendor_images.count(), 2)
        for img in vendor_images:
            self.assertEqual(img.product, self.product)
            self.assertEqual(img.image_type, 'gallery')
