# Generated by Django 5.1.4 on 2025-01-25 21:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0004_alter_rewardearned_reward_and_more'),
        ('p2pmb', '0006_package'),
        ('payment_app', '0002_alter_transaction_transaction_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='package',
            field=models.ManyToManyField(blank=True, to='p2pmb.package'),
        ),
        migrations.AddField(
            model_name='investment',
            name='transaction_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='payment_app.transaction'),
        ),
        migrations.AlterField(
            model_name='investment',
            name='investment_type',
            field=models.CharField(choices=[('super_agency', 'Super Agency'), ('agency', 'Agency'), ('field_agent', 'Field Agent'), ('p2pmb', 'Person 2 Person')], max_length=20),
        ),
    ]
