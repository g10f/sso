# Generated by Django 1.11.3 on 2017-07-02 12:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('l10n', '0002_country_last_modified'),
    ]

    operations = [
        migrations.AlterField(
            model_name='country',
            name='admin_area',
            field=models.CharField(blank=True, choices=[('a', 'Another'), ('i', 'Island'), ('ar', 'Arrondissement'), ('at', 'Atoll'), ('ai', 'Autonomous island'), ('ca', 'Canton'), ('cm', 'Commune'), ('co', 'County'), ('dp', 'Department'), ('de', 'Dependency'), ('dt', 'District'), ('dv', 'Division'), ('em', 'Emirate'), ('gv', 'Governorate'), ('ic', 'Island council'), ('ig', 'Island group'), ('ir', 'Island region'), ('kd', 'Kingdom'), ('mu', 'Municipality'), ('pa', 'Parish'), ('pf', 'Prefecture'), ('pr', 'Province'), ('rg', 'Region'), ('rp', 'Republic'), ('sh', 'Sheading'), ('st', 'State'), ('sd', 'Subdivision'), ('sj', 'Subject'), ('ty', 'Territory')], max_length=2, null=True, verbose_name='Administrative Area'),
        ),
        migrations.AlterField(
            model_name='country',
            name='continent',
            field=models.CharField(choices=[('AF', 'Africa'), ('NA', 'North America'), ('EU', 'Europe'), ('AS', 'Asia'), ('OC', 'Oceania'), ('SA', 'South America'), ('AN', 'Antarctica')], max_length=2, verbose_name='Continent'),
        ),
    ]
