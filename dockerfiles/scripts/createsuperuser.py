from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin')

if not User.objects.filter(username='test').exists():
    User.objects.create_superuser('test', 'test@test.com', 'test')
