# Generated by Django 5.1.4 on 2025-02-28 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('p2pmb', '0014_mlmtree_is_working_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='mlmtree',
            name='is_show',
            field=models.BooleanField(default=True),
        ),
    ]
