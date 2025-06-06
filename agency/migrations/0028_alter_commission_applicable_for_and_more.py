# Generated by Django 5.1.4 on 2025-05-04 23:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0027_alter_commission_options_commission_applicable_for_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commission',
            name='applicable_for',
            field=models.CharField(choices=[('super_agency', 'Super Agency'), ('agency', 'Agency'), ('field_agent', 'field_agent')], default='super_agency', max_length=15),
        ),
        migrations.AlterField(
            model_name='commission',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
