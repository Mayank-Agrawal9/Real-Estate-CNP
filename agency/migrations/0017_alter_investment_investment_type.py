# Generated by Django 5.1.4 on 2025-02-28 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0016_investment_pay_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='investment',
            name='investment_type',
            field=models.CharField(choices=[('super_agency', 'Super Agency'), ('agency', 'Agency'), ('field_agent', 'Field Agent'), ('customer', 'Customer'), ('p2pmb', 'Person 2 Person')], max_length=20),
        ),
    ]
