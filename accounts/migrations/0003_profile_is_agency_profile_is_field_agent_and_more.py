# Generated by Django 5.1.4 on 2025-02-11 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_faq_softwarepolicy'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_agency',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_field_agent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_p2pmb',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_super_agency',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='profile',
            name='kyc_video',
            field=models.FileField(blank=True, null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='profile',
            name='mobile_number1',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='mobile_number2',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='other_email',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='pan_remarks',
            field=models.TextField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='voter_number',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
