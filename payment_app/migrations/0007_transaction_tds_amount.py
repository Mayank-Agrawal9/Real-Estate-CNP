# Generated by Django 5.1.4 on 2025-06-12 01:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment_app', '0006_userwallet_tds_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='tds_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
