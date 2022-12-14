# Generated by Django 4.1.1 on 2022-12-08 20:53

from django.db import migrations


CONV_TABLE = [
    ('nodes.logics.SimpleCheapestHours', 'nodes.logics.simple_cheapest_hours.SimpleCheapestHours'),
    ('nodes.logics.TapoP100', 'nodes.logics.tapo_p100.TapoP100'),
    ('nodes.logics.Clock', 'nodes.logics.clock.Clock'),
    ('nodes.logics.MelCloud', 'nodes.logics.melcloud.MelCloud'),
]


def convert(apps, conv_table):
    Node = apps.get_model('nodes', 'Node')

    conv_dict = {old: new for old, new in conv_table}

    for node in Node.objects.all():
        node.logic_class = conv_dict.get(node.logic_class)
        if node.logic_class:
            node.save(update_fields=['logic_class'])


def convert_to_new_classes(apps, schema_editor):
    convert(apps, CONV_TABLE)


def convert_to_old_classes(apps, schema_editor):
    convert(apps, [(new, old) for old, new in CONV_TABLE])


class Migration(migrations.Migration):

    dependencies = [
        ('nodes', '0003_node_pos'),
    ]

    operations = [
        migrations.RunPython(convert_to_new_classes, convert_to_old_classes),
    ]
