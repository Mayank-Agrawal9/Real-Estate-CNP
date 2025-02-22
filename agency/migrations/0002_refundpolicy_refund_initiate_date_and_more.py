# Generated by Django 5.1.4 on 2025-01-13 02:24

import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='refundpolicy',
            name='refund_initiate_date',
            field=models.DateField(default=datetime.datetime(2025, 1, 13, 2, 24, 21, 662491)),
        ),
        migrations.AddField(
            model_name='refundpolicy',
            name='refund_process_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='refund_process_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='refundpolicy',
            name='refund_process_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='refundpolicy',
            name='refund_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='refundpolicy',
            name='refund_type',
            field=models.CharField(choices=[('1_month', 'Refund within 1 month'), ('3_month', 'Refund within 3 months'), ('6_month', 'Refund within 6 months'), ('1_year', 'Refund within 1 year'), ('no_refund', 'No Refund after 1 year')], default='no_refund', max_length=20),
        ),
        migrations.CreateModel(
            name='PPDAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('deposit_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('deposit_date', models.DateField(auto_now_add=True)),
                ('monthly_rental', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('has_purchased_property', models.BooleanField(default=False)),
                ('withdrawal_date', models.DateField(blank=True, null=True)),
                ('withdrawal_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ppd_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.DeleteModel(
            name='PPDModel',
        ),
    ]
