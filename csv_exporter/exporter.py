from __future__ import unicode_literals

import os
import tempfile
import csv
import uuid
import datetime
from zipfile import ZipFile
import logging

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.utils.encoding import smart_text
from django.db.models.query import QuerySet
from django.db.models import FileField, sql
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.sites.models import Site


logger = logging.getLogger(__name__)


def export_field(obj, field, dir, zipfile):
    fields = field.split('.')

    def _export_field(obj, fields):
        field = fields[0]
        if hasattr(obj, field):
            value = getattr(obj, field)
            if callable(value):
                value = value()
            elif hasattr(value, 'field'):
                modelField = value.field
                if ((hasattr(modelField, 'many_to_many') and modelField.many_to_many) or
                   (hasattr(modelField, 'many_to_one') and modelField.many_to_one)):
                    if len(fields) > 1:
                        return [_export_field(item, fields[1:]) for item in value.all()]
                    else:
                        return [smart_text(item) for item in value.all()]
                elif isinstance(modelField, FileField):
                    if len(fields) is 1:
                        new_file_name = os.path.join(dir, value.name)
                        if not os.path.isdir(os.path.dirname(new_file_name)):
                            os.makedirs(os.path.dirname(new_file_name))
                        with open(new_file_name, mode='w+b') as f:
                            for chunk in value.chunks():
                                f.write(chunk)
                        arcname = os.path.join('./', force_text(value.name))
                        zipfile.write(new_file_name, arcname=arcname)
                        os.remove(new_file_name)
                        return '=HYPERLINK("{}")'.format(arcname)
            if len(fields) > 1:
                return _export_field(value, fields[1:])
            else:
                return force_text(value)
        else:
            raise AttributeError('{} does not have attribute {}. Available attributes are {}'.format(obj, field, dir(obj)))

    return _export_field(obj, fields)


def export_resource(obj, attributes, dir, zipfile):
    resource = {}
    for field in attributes:
        resource.update({force_text(field): export_field(obj, field, dir, zipfile)})
    return resource


def send_email_to_user(file_url, timedelta, emails, subject='Your data export is ready'):
    text = 'Your data export is now ready. It will be available for the next {} days. {}'.format(timedelta.days, file_url)
    html = '<html><body><div>Your data export is now ready. It will be available for the next {} days. <a href="{}">Your Zip File</a></div></body></html>'.format(timedelta.days, file_url)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email='{}'.format(settings.DEFAULT_FROM_EMAIL),
        to=emails,
    )
    mail.attach_alternative(html, 'text/html')
    try:
        mail.send(fail_silently=False)
    except Exception as e:
        logger.debug('Exporter failed sending email: {}'.format(e))


def get_protocol():
    protocol = 'http'
    if settings.SECURE_SSL_REDIRECT:
        protocol = 'https'
    # Used for projects that support protcol settings
    if hasattr(settings, 'PROTOCOL'):
        protocol = settings.PROTOCOL
    return protocol


def export(query_or_queryset, attributes, callback=None, timedelta=datetime.timedelta(days=2)):
    with tempfile.TemporaryDirectory() as tmpdirname:
        zip_path = os.path.join(tmpdirname, 'data.zip')
        with ZipFile(zip_path, mode='w') as zipfile:
            csv_path = os.path.join(tmpdirname, 'data.csv')
            with open(csv_path, mode='w+') as tempcsv:
                csv_writer = csv.DictWriter(tempcsv, fieldnames=[force_text(field) for field in attributes])
                csv_writer.writeheader()
                if isinstance(query_or_queryset, sql.Query):
                    queryset = QuerySet(query=query_or_queryset)
                else:
                    queryset = query_or_queryset

                if isinstance(queryset, QuerySet):
                    # Iterate without the queryset cache, to avoid wasting memory when
                    # exporting large datasets.
                    iterable = queryset.iterator()
                else:
                    iterable = queryset
                for obj in iterable:
                    csv_writer.writerow(export_resource(obj, attributes, tmpdirname, zipfile))
            zipfile.write(csv_path, arcname='data.csv')

        zip_name = 'exports/{}.zip'.format(uuid.uuid4())
        while default_storage.exists(zip_name):
            zip_name = 'exports/{}.zip'.format(uuid.uuid4())
        with open(zip_path, 'rb') as f:
            default_storage.save(zip_name, f)

        zip_url = zip_name
        if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto.S3BotoStorage':
            key = default_storage._normalize_name(default_storage._clean_name(zip_name))
            default_storage.bucket.set_acl(
                'private', key_name=key)
            zip_url = default_storage.url(zip_name, expire=timedelta.total_seconds())
        else:
            zip_url = default_storage.url(zip_name)
        if not zip_url.startswith('http'):
            protocol = get_protocol()
            zip_url = '{}://{}{}'.format(protocol,
                                         Site.objects.get_current().domain,
                                         zip_url)

        if callback:
            callback(zip_url, timedelta)

    return zip_url
