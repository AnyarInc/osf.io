# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-03-12 18:25
from __future__ import unicode_literals

import datetime
from itertools import islice, chain

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from django.db.models import F
from django.db.models import OuterRef, Subquery
from guardian.shortcuts import assign_perm, get_perms, remove_perm
from django.core.management.sql import emit_post_migrate_signal
from bulk_update.helper import bulk_update
from osf.models import OSFUser
from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from osf.models import Preprint

node_preprint_logs = [
    'contributor_added',
    'contributor_removed',
    'contributors_reordered',
    'edit_description',
    'edit_title',
    'made_contributor_invisible',
    'made_contributor_visible',
    'made_private',
    'made_public',
    'permissions_updated',
    'preprint_file_updated',
    'preprint_initiated',
    'preprint_license_updated',
    'subjects_updated',
    'tag_added',
    'tag_removed'
]

def pull_preprint_date_modified_from_node(node, preprint):
    latest_log_date = node.logs.filter(action__in=node_preprint_logs).order_by('date').last().date
    if preprint.modified < latest_log_date:
        return latest_log_date
    return preprint.modified

def reverse_func(apps, schema_editor):
    PreprintContributor = apps.get_model('osf', 'PreprintContributor')
    PreprintTags = apps.get_model('osf', 'Preprint_Tags')
    NodeSettings = apps.get_model('addons_osfstorage', 'NodeSettings')

    preprints = []
    files = []
    nodes = []
    for preprint in Preprint.objects.filter(node__isnull=False).select_related('node'):
        node = preprint.node
        modified_field = Preprint._meta.get_field('modified')
        modified_field.auto_now = False
        preprint.modified = pull_preprint_date_modified_from_node(node, preprint)

        node_modified_field = AbstractNode._meta.get_field('modified')
        node_modified_field.auto_now = False

        preprint.title = 'Untitled'
        preprint.description = ''
        preprint.creator = None
        preprint.article_doi = ''
        preprint.is_public = True
        preprint.region_id = None
        preprint.spam_status = None
        preprint.spam_pro_tip = ''
        preprint.spam_data = {}
        preprint.date_last_reported = None
        preprint.reports = {}

        preprint.root_folder = None
        preprint_file = preprint.primary_file
        preprint_file.target = node
        node.preprint_file = preprint_file
        preprint_file.parent_id = NodeSettings.objects.get(owner_id=node.id).root_node_id

        preprint.deleted = None
        preprint.migrated = None

        preprints.append(preprint)
        nodes.append(node)
        files.append(preprint_file)

        # Deleting the particular preprint admin/read/write groups will remove the users from the groups
        # and their permission to these preprints
        Group.objects.get(name=format_group(preprint, 'admin')).delete()
        Group.objects.get(name=format_group(preprint, 'write')).delete()
        Group.objects.get(name=format_group(preprint, 'read')).delete()

    PreprintContributor.objects.all().delete()
    PreprintTags.objects.all().delete()
    bulk_update(preprints, update_fields=['title', 'description', 'creator', 'article_doi', 'is_public', 'region_id', 'deleted', 'migrated', 'modified', 'primary_file', 'spam_status', 'spam_pro_tip', 'spam_data', 'date_last_reported', 'reports', 'root_folder'])
    bulk_update(nodes, update_fields=['preprint_file'])
    bulk_update(files)

def batch(iterable, size):
    sourceiter = iter(iterable)
    while True:
        batchiter = islice(sourceiter, size)
        yield chain([batchiter.next()], batchiter)

def divorce_preprints_from_nodes(apps, schema_editor):
    # this is to make sure that the permissions created earlier exist!
    emit_post_migrate_signal(2, False, 'default')

    AbstractNode = apps.get_model('osf', 'AbstractNode')
    PreprintContributor = apps.get_model('osf', 'PreprintContributor')
    PreprintTags = apps.get_model('osf', 'Preprint_Tags')
    NodeSettings = apps.get_model('addons_osfstorage', 'NodeSettings')
    # OsfStorageFolder = apps.get_model('osf', 'OsfStorageFolder')

    contributors = []
    preprints = []
    tags = []
    files = []
    nodes = []

    for preprint in Preprint.objects.filter(node__isnull=False).select_related('node'):
        node = preprint.node
        preprint_content_type = ContentType.objects.get_for_model(Preprint)

        modified_field = Preprint._meta.get_field('modified')
        modified_field.auto_now = False
        preprint.modified = pull_preprint_date_modified_from_node(node, preprint)

        preprint.title = node.title
        preprint.description = node.description
        preprint.creator = node.logs.filter(action='preprint_initiated').first().user
        preprint.article_doi = node.preprint_article_doi
        preprint.is_public = node.is_public

        preprint.region_id = NodeSettings.objects.get(owner_id=node.id).region_id
        preprint.spam_status = node.spam_status
        preprint.spam_pro_tip = node.spam_pro_tip
        preprint.spam_data = node.spam_data
        preprint.date_last_reported = node.date_last_reported
        preprint.reports = node.reports

        root_folder = OsfStorageFolder(name='', target=preprint, is_root=True)
        root_folder.save()
        preprint.root_folder = root_folder
        preprint_file = OsfStorageFile.objects.get(id=node.preprint_file.id)
        preprint_file.target = preprint
        preprint.primary_file_id = preprint_file.id
        preprint_file.parent = root_folder

        deleted_log = node.logs.filter(action='project_deleted').first()
        preprint.deleted = deleted_log.date if deleted_log else None

        preprint.migrated = datetime.datetime.now()

        # use bulk create
        admin = []
        write = []
        read = []

        for tag in node.tags.all():
            tags.append(PreprintTags(preprint_id=preprint.id, tag_id=tag.id))

        for contrib in node.contributor_set.all():
            # make a PreprintContributor that points to the pp instead of the node
            # because there's a throughtable, relations are designated
            # solely on the through model, and adds on the related models
            # are not required.

            new_contrib = PreprintContributor(
                preprint_id=preprint.id,
                user_id=contrib.user.id,
                visible=contrib.visible,
                _order=contrib._order
            )
            contributors.append(new_contrib)
            if contrib.admin:
                admin.append(contrib.user)
            elif contrib.write:
                write.append(contrib.user)
            else:
                read.append(contrib.user)

        update_group_permissions(preprint)

        add_users_to_group(Group.objects.get(name=format_group(preprint, 'admin')), admin)
        add_users_to_group(Group.objects.get(name=format_group(preprint, 'write')), write)
        add_users_to_group(Group.objects.get(name=format_group(preprint, 'read')), read)

        preprints.append(preprint)
        files.append(preprint_file)

    batch_size = 1000
    for batchiter in batch(contributors, batch_size):
        PreprintContributor.objects.bulk_create(batchiter)

    batch_size = 1000
    for batchiter in batch(tags, batch_size):
        PreprintTags.objects.bulk_create(batchiter)

    bulk_update(preprints, update_fields=['title', 'description', 'creator', 'article_doi', 'is_public', 'region_id', 'deleted', 'migrated', 'modified', 'primary_file', 'spam_status', 'spam_pro_tip', 'spam_data', 'date_last_reported', 'reports', 'root_folder'])
    bulk_update(files)

group_format = 'preprint_{self.id}_{group}'

def format_group(self, name):
    return group_format.format(self=self, group=name)

def update_group_permissions(self):
    for group_name, group_permissions in groups.items():
        group, created = Group.objects.get_or_create(name=format_group(self, group_name))
        to_remove = set(get_perms(group, self)).difference(group_permissions)
        for p in to_remove:
            remove_perm(p, group, self)
        for p in group_permissions:
            assign_perm(p, group, self)

groups = {
    'read': ('read_preprint',),
    'write': ('read_preprint', 'write_preprint',),
    'admin': ('read_preprint', 'write_preprint', 'admin_preprint',)
}

def add_users_to_group(group, user_list):
    for user in user_list:
        group.user_set.add(OSFUser.objects.get(id=user.id))

class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0108_add_preprint_partial_index'),
    ]

    operations = [
        migrations.RunPython(divorce_preprints_from_nodes, reverse_func)
    ]