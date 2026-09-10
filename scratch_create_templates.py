import os

base_dir = r"c:\Users\Ankit kumar\Documents\Library Management System\templates\admin"
os.makedirs(base_dir, exist_ok=True)

files = {
    "issues.html": """{% extends "base.html" %}
{% block title %}Issues{% endblock %}
{% block content %}
<h2>Issues</h2>
<table class="table">
  <tr><th>Book</th><th>Member</th><th>Status</th></tr>
  {% for issue in issues.items %}
  <tr>
    <td>{{ issue.book.title }}</td>
    <td>{{ issue.member.full_name }}</td>
    <td>{{ issue.status }}</td>
  </tr>
  {% endfor %}
</table>
{% endblock %}""",

    "fines.html": """{% extends "base.html" %}
{% block title %}Fines{% endblock %}
{% block content %}
<h2>Fines</h2>
<table class="table">
  <tr><th>Member</th><th>Amount</th><th>Status</th></tr>
  {% for fine in fines.items %}
  <tr>
    <td>{{ fine.member.full_name }}</td>
    <td>{{ fine.amount }}</td>
    <td>{{ fine.status }}</td>
  </tr>
  {% endfor %}
</table>
{% endblock %}""",

    "settings.html": """{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<h2>Settings</h2>
<form method="POST">
  {{ form.hidden_tag() }}
  {% for field in form if field.name != 'csrf_token' %}
    <div class="mb-3">
      {{ field.label }} {{ field(class="form-control") }}
    </div>
  {% endfor %}
  <button type="submit" class="btn btn-primary">Save</button>
</form>
{% endblock %}""",

    "activity_log.html": """{% extends "base.html" %}
{% block title %}Activity Log{% endblock %}
{% block content %}
<h2>Activity Log</h2>
<table class="table">
  <tr><th>User</th><th>Activity</th><th>Date</th></tr>
  {% for log in logs.items %}
  <tr>
    <td>{{ log.user.full_name if log.user else 'System' }}</td>
    <td>{{ log.description }}</td>
    <td>{{ log.created_at }}</td>
  </tr>
  {% endfor %}
</table>
{% endblock %}"""
}

for name, content in files.items():
    with open(os.path.join(base_dir, name), 'w', encoding='utf-8') as f:
        f.write(content)
print("Created missing admin templates.")
