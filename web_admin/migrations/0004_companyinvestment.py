# Generated by Django 5.1.4 on 2025-04-13 01:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web_admin', '0003_functionalityaccesspermissions_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyInvestment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('applicable_for', models.CharField(choices=[('p2pmb', 'P2PMB'), ('super_agency', 'Super Agency'), ('agency', 'Agency'), ('field_agent', 'Field Agent')], default='p2pmb', max_length=20)),
                ('investment_type', models.CharField(blank=True, choices=[('direct', 'Direct'), ('level', 'Level'), ('reward', 'Reward'), ('royalty', 'Royalty'), ('core_team', 'Core Team'), ('company_expense', 'Company Expense'), ('diwali_gift', 'Diwali Gift'), ('donation', 'Donation'), ('interest', 'Interest'), ('property', 'Property'), ('crypto', 'Crypto'), ('trading', 'Trading')], max_length=20, null=True)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=25)),
                ('initiated_date', models.DateField()),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'verbose_name': 'Company Investment',
                'verbose_name_plural': 'Company Investment Distribution',
            },
        ),
    ]
