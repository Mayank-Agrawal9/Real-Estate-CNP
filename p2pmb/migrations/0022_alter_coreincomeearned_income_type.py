# Generated by Django 5.1.4 on 2025-03-27 02:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('p2pmb', '0021_coreincomeearned'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coreincomeearned',
            name='income_type',
            field=models.CharField(choices=[('tour', 'tour'), ('income', 'income')], default='income', max_length=20),
        ),
    ]
