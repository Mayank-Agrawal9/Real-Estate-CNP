# Generated by Django 5.1.4 on 2025-01-13 01:16

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('transaction_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('taxable_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('transaction_type', models.CharField(choices=[('investment', 'Investment'), ('deposit', 'Deposit'), ('withdraw', 'Withdraw'), ('send', 'Send'), ('transfer', 'Transfer'), ('reward', 'Reward'), ('commission', 'Commission'), ('refund', 'Refund'), ('rent', 'Rent')], max_length=10)),
                ('transaction_status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('payment_slip', models.ImageField(blank=True, null=True, upload_to='payment_slips/')),
                ('payment_method', models.CharField(blank=True, choices=[('neft', 'NEFT'), ('rtgs', 'RTGS'), ('upi', 'UPI'), ('cards', 'Cards'), ('wallet', 'Wallet'), ('bank_transfer', 'Bank transfer'), ('cheque', 'Cheque')], max_length=50, null=True)),
                ('deposit_transaction_id', models.CharField(blank=True, max_length=200, null=True)),
                ('remarks', models.TextField(blank=True, null=True)),
                ('verified_on', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('receiver', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_transactions', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_transactions', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UserWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='Date of creation')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date of update')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], default='active', max_length=20)),
                ('main_wallet_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('app_wallet_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
