# Generated by Django 2.0.4 on 2018-04-24 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organisations', '0030_auto_20180301_2243'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='transregional_distance',
            field=models.DecimalField(blank=True, decimal_places=3, help_text='Distance used for calculations of transregional events [km].', max_digits=8, null=True, verbose_name='transregional distance'),
        ),
    ]
