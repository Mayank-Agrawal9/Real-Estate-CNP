# Generated by Django 5.1.4 on 2025-03-06 02:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment_app', '0003_alter_transaction_payment_method_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(choices=[('investment', 'Investment'), ('deposit', 'Deposit'), ('deduct', 'Deduct'), ('withdraw', 'Withdraw'), ('send', 'Send'), ('receive', 'Receive'), ('transfer', 'Transfer'), ('reward', 'Reward'), ('commission', 'Commission'), ('refund', 'Refund'), ('rent', 'Rent'), ('interest', 'Interest')], max_length=10),
        ),
    ]
