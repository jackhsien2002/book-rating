# Books

# Introduction
Readers are eager to share their review on a book in public. Books is a book review website. Users are able to registered for this website and login with their account. Once they login, users can search for books they want to review and give rate on.

# Package
Flask==1.1.1
Flask-Session==0.3.1
Jinja2==2.10.3
psycopg2-binary==2.8.4
SQLAlchemy==1.3.10

# Feature
1. When user enters Books website, they can signup an account and login with a username and password. If user try to sign up a account that has been in database, error messages will be displayed on the page.
2. Once they login, they can search for books they want. There are three search fields, including isbn, title and author. Once these fields are submitted to Flask backend, they are translated to query string and sent to goodread. The result of query will be listed by revelance that are defined by goodread algorithms.
3. When user click on any link on the list, book detail will be displayed in term of isnb, title, author, publish year, average rating and rating counts.
4. If detail of that particular book has not been viewed before, Flask backend will query detail of that book from goodread and store query result of that book in database
# Demo

