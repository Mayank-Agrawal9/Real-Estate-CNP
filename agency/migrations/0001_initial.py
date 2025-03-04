# Generated by Django 5.1.4 on 2025-01-13 01:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Agency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('name', models.CharField(max_length=250)),
                ('type', models.CharField(choices=[('private_company', 'Private Company'), ('one_person_company', 'One Person Company'), ('public_company', 'Public Company'), ('llp', 'LLP'), ('enterprise', 'Enterprise')], default='enterprise', max_length=250)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('pan_number', models.CharField(blank=True, max_length=10, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('office_address', models.TextField(blank=True, null=True)),
                ('turnover', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Commission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('commission_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('commission_type', models.CharField(max_length=255)),
                ('is_paid', models.BooleanField(default=False)),
                ('commission_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_by', to=settings.AUTH_USER_MODEL)),
                ('commission_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commission_to', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FieldAgent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('turnover', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('agency', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='field_agents', to='agency.agency')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='field_agent', to='accounts.profile')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FundWithdrawal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('withdrawal_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('withdrawal_date', models.DateTimeField(auto_now_add=True)),
                ('is_paid', models.BooleanField(default=False)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawal_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('investment_type', models.CharField(choices=[('super_agency', 'Super Agency'), ('agency', 'Agency'), ('field_agent', 'Field Agent')], max_length=20)),
                ('gst', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PPDModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('deposit_amount', models.DecimalField(decimal_places=2, max_digits=15)),
                ('monthly_rental', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ppd_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RefundPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('refund_type', models.CharField(choices=[('1_month', 'Refund within 1 month'), ('3_month', 'Refund within 3 months'), ('6_month', 'Refund within 6 months'), ('1_year', 'Refund within 1 year'), ('no_refund', 'No Refund after 1 year')], max_length=20)),
                ('amount_refunded', models.DecimalField(decimal_places=2, max_digits=15)),
                ('deduction_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refund_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Reward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('reward_type', models.CharField(choices=[('android_mobile', 'Android Mobile'), ('goa_tour', 'Goa Tour'), ('bangkok_tour', 'Bangkok Tour'), ('dubai_tour', 'Dubai Tour'), ('bullet_bike', 'Bullet Bike'), ('car_fund', 'Car Fund'), ('foreign_trip', 'Foreign Trip'), ('fully_paid_vacation', 'Fully Paid Vacation'), ('studio_flat', 'Studio Flat'), ('car_fund_full_paid', 'Car Fund (Full Paid)'), ('villa', 'Villa'), ('helicopter', 'Helicopter'), ('yacht', 'Yacht')], max_length=50)),
                ('reward_value', models.DecimalField(decimal_places=2, max_digits=15)),
                ('turnover_threshold', models.DecimalField(decimal_places=2, max_digits=15)),
                ('achieved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reward_user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SuperAgency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('name', models.CharField(max_length=250)),
                ('type', models.CharField(choices=[('private_company', 'Private Company'), ('one_person_company', 'One Person Company'), ('public_company', 'Public Company'), ('llp', 'LLP'), ('enterprise', 'Enterprise')], default='enterprise', max_length=250)),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('pan_number', models.CharField(blank=True, max_length=10, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('office_address', models.TextField(blank=True, null=True)),
                ('office_area', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('income', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('turnover', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('max_agencies', models.PositiveIntegerField(default=100)),
                ('max_field_agents', models.PositiveIntegerField(default=10000)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('profile', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_company', to='accounts.profile')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='RewardEarned',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('earned_at', models.DateTimeField(auto_now_add=True)),
                ('turnover_at_earning', models.DecimalField(decimal_places=2, max_digits=15)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('reward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='agency.reward')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rewards_earned', to='agency.superagency')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='agency',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agencies', to='agency.superagency'),
        ),
    ]
