# EC2 Flask Registration and File Portal

A rubric-complete Flask application using SQLite, Apache, and mod_wsgi. A user can register with basic details, upload a `.txt` file, view the stored information and file word count, download the file, log out, and log back in to retrieve the same profile.

## Features

- Registration with username, password, first name, last name, email, and address
- Password hashing with Werkzeug
- SQLite persistence
- `.txt` upload with a 1 MB size limit and collision-safe stored filename
- Server-side word count
- Profile display and authenticated download
- Logout and re-login flow
- Responsive interface

## Project structure

```text
ec2_flask_assignment/
├── app.py
├── flaskapp.wsgi
├── requirements.txt
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── profile.html
│   └── register.html
└── uploads/
    └── .gitkeep
```

`users.db` and uploaded files are created at runtime and intentionally excluded from Git.

## Test locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## EC2 setup

Launch Ubuntu Server 24.04 LTS on a Free Tier eligible instance. Configure its security group with:

- SSH, TCP port 22, source **My IP**
- HTTP, TCP port 80, source `0.0.0.0/0`

Connect using the SSH command supplied by the EC2 console, then install packages:

```bash
sudo apt update
sudo apt install -y apache2 libapache2-mod-wsgi-py3 python3 python3-pip python3-flask sqlite3 git
```

Clone your GitHub repository and deploy the project:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
sudo mkdir -p /var/www/flaskapp
sudo cp -R YOUR-REPOSITORY/. /var/www/flaskapp/
sudo chown -R ubuntu:www-data /var/www/flaskapp
sudo chmod 775 /var/www/flaskapp /var/www/flaskapp/uploads
```

The final `chmod` command should be run after `users.db` exists. Importing the app once creates it:

```bash
cd /var/www/flaskapp
python3 -c "from app import app; print('Database initialized')"
sudo chown ubuntu:www-data /var/www/flaskapp/users.db
sudo chmod 664 /var/www/flaskapp/users.db
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Edit `/var/www/flaskapp/app.py` and replace `change-this-to-a-long-random-value` with the generated value.

Create the Apache virtual-host configuration:

```bash
sudo nano /etc/apache2/sites-available/flaskapp.conf
```

Paste:

```apache
<VirtualHost *:80>
    ServerName YOUR-EC2-PUBLIC-DNS

    WSGIDaemonProcess flaskapp user=www-data group=www-data threads=5
    WSGIScriptAlias / /var/www/flaskapp/flaskapp.wsgi

    <Directory /var/www/flaskapp>
        WSGIProcessGroup flaskapp
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>

    Alias /static /var/www/flaskapp/static
    <Directory /var/www/flaskapp/static>
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/flaskapp-error.log
    CustomLog ${APACHE_LOG_DIR}/flaskapp-access.log combined
</VirtualHost>
```

Enable the site and restart Apache:

```bash
sudo a2dissite 000-default.conf
sudo a2ensite flaskapp.conf
sudo apache2ctl configtest
sudo systemctl restart apache2
sudo systemctl status apache2 --no-pager
```

Visit `http://YOUR-EC2-PUBLIC-DNS`.

If the site fails, inspect the application log:

```bash
sudo tail -n 50 /var/log/apache2/flaskapp-error.log
```

## Verify SQLite on EC2

```bash
cd /var/www/flaskapp
sqlite3 users.db
```

Inside SQLite:

```sql
.tables
.schema users
SELECT id, username, first_name, last_name, email, address, original_filename, word_count FROM users;
.exit
```

## Recommended assignment screenshots

1. EC2 **Launch an instance** page showing the instance name.
2. Ubuntu Server 24.04 LTS AMI selected and marked Free Tier eligible.
3. Free Tier eligible instance type.
4. Key-pair creation dialog (never show or upload the private key contents).
5. Network settings showing SSH from My IP and HTTP from Anywhere.
6. EC2 Instances page showing `Running`, both status checks passed, public IPv4 DNS, and public IPv4 address.
7. SSH terminal after the Apache, mod_wsgi, Python, pip, Flask, and SQLite installation command completes.
8. `python3 --version`, `pip3 --version`, `apache2 -v`, `sqlite3 --version`, and `python3 -c "import flask; print(flask.__version__)"` output.
9. SQLite `.schema users` output.
10. Browser registration page with all fields and the upload control.
11. Profile page after submission showing the saved details, filename, word count, and download button.
12. Login page after logout.
13. Retrieved profile after re-login.
14. GitHub repository page showing the source files.
15. Browser address bar showing the EC2 public URL.

Do not place real passwords, the `.pem` private key, AWS account numbers, or other secrets in screenshots or GitHub.
