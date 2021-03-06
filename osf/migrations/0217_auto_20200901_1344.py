# -*- coding: utf-8 -*-
# Generated by Django 1.11.28 on 2020-09-01 13:44
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import osf.models.base


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0216_auto_20200910_1259'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistrationRequestAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('_id', models.CharField(db_index=True, default=osf.models.base.generate_object_id, max_length=24, unique=True)),
                ('trigger', models.CharField(choices=[('submit', 'Submit'), ('accept', 'Accept'), ('reject', 'Reject'), ('edit_comment', 'Edit_Comment')], max_length=31)),
                ('from_state', models.CharField(choices=[('initial', 'Initial'), ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], max_length=31)),
                ('to_state', models.CharField(choices=[('initial', 'Initial'), ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], max_length=31)),
                ('comment', models.TextField(blank=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('auto', models.BooleanField(default=False)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, osf.models.base.QuerySetExplainMixin),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='date_last_transitioned',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='draftregistration',
            name='machine_state',
            field=models.CharField(choices=[('initial', 'Initial'), ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'), ('pending_embargo', 'Pending_Embargo'), ('embargo', 'Embargo'), ('pending_embargo_termination', 'Pending_Embargo_Termination'), ('pending_withdraw', 'Pending_Withdraw')], db_index=True, default='initial', max_length=30),
        ),
        migrations.AddField(
            model_name='registrationrequestaction',
            name='target',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registration_actions', to='osf.DraftRegistration'),
        ),
    ]
