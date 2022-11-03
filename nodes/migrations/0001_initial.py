# Generated by Django 4.1.1 on 2022-09-28 17:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('logic_class', models.CharField(max_length=200)),
                ('settings', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Connection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_key', models.CharField(max_length=50)),
                ('dest_key', models.CharField(max_length=50)),
                ('dest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inputs', to='nodes.node')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outputs', to='nodes.node')),
            ],
        ),
    ]