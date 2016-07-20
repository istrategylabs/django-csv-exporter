# CSV Exporter

This Django package is a model exporter that can be run in a delayed task and emails a link to the resulting zip file containing a csv and all files.

## How to use

### To install the package

```
pip install django-csv-exporter
```

### To use the package

```
def export(queryset, attributes, callback=None, timedelta=datetime.timedelta(days=2)):
```

```
from datetime import timedelta
from functools import partial
from csv_exporter import export, send_email_to_user

users = UserProfile.objects.filter(team='myteam', active=True)
callback = partial(send_email_to_user, ['email1@gmail.com', 'email2@gmail.com'])
zip_url = export(users, ('full_name', 'profile_picture', 'team.name', 'date_joined.isoformat'), callback, timedelta(days=2))
```

The function `send_email_to_user` is a helper function to send the zip_url to the users. The callback to export needs to accept the parameters (zip_url, timedelta). Timedelta is a length of time the url is valid for. Expiration works only for django-storages using s3-boto, otherwise the regular url is returned.

### With Django RQ

```
import django_rq
django_rq.enqueue(export, users, ('full_name', 'profile_picture', 'team.name', 'date_joined.isoformat'), callback, timedelta(days=2))
```
