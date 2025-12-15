from django.urls import path

from vendor.views import *

urlpatterns = [
    path('categories/', CategoryListCreateAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailAPIView.as_view(), name='category-detail'),
    path('cities/by-state/<int:state_id>/', CityByStateAPIView.as_view(), name='city-by-state'),
    path('vendors/', VendorListCreateAPIView.as_view(), name='vendor-list'),
    path('request-vendors/', RequestVendorDetailAPIView.as_view(), name='request-vendor-detail'),
    path('vendors/search/', VendorSearchAPIView.as_view(), name='vendor-search'),
    path('vendors/stats/', VendorStatsAPIView.as_view(), name='vendor-stats'),
    path('vendors/<int:vendor_id>/images/', VendorImageListAPIView.as_view(), name='vendor-image-list'),
    path('vendors/<int:vendor_id>/images/upload/', VendorImageUploadAPIView.as_view(), name='vendor-image-upload'),
    path('vendor-images/<int:pk>/', VendorImageDetailAPIView.as_view(), name='vendor-image-detail'),
    path('vendors/<int:vendor_id>/products/', VendorProductListCreateAPIView.as_view(), name='vendor-product-list'),
    path('products/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),
    path('vendors/<int:vendor_id>/ratings/', VendorRatingListCreateAPIView.as_view(), name='vendor-rating-list'),
    path('ratings/<int:pk>/', RatingDetailAPIView.as_view(), name='rating-detail'),
    path('vendors/<int:vendor_id>/enquire/', VendorEnquiryCreateAPIView.as_view(), name='vendor-enquiry-create'),
    path('enquiries/', EnquiryListAPIView.as_view(), name='enquiry-list'),
    path('enquiries/<int:pk>/', EnquiryDetailAPIView.as_view(), name='enquiry-detail'),
    path('vendors/<int:vendor_id>/certifications/', VendorCertificationListCreateAPIView.as_view(),
         name='vendor-certification-list'),
    path('vendors/<int:vendor_id>/awards/', VendorAwardListCreateAPIView.as_view(), name='vendor-award-list'),
]