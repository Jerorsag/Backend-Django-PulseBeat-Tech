# Generated by Django 5.1.7 on 2025-03-20 02:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0004_alter_transaction_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='status',
            field=models.BooleanField(default='pending', max_length=20),
        ),
    ]
