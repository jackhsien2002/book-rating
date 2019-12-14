# Books

# Introduction
Readers are eager to share their review on a book in public. Books is a book review website. Users are able to registered for this website and login with their account. Once they login, users can search for books they want to review and give rate on.

# Package
Please refers to requirement.txt for more details
In Flask, Celery act as a broker, which issue the tasks from queue to worker(redis). Worker can perform tasks in background of Flask while Flask proceed to do other tasks. The common usage include email sending. To send a email, user has to wait for a long time until email server responds. With Celery, user can get instant response from Flask while worker is working on sending the email behind the scene


# Feature
1. When user enters Books website, they can signup an account and login with a username and password. If user try to sign up a account that has been in database, error messages will be displayed on the page.
2. Once they login, they can search for books they want. There are three search fields, including isbn, title and author. Once these fields are submitted to Flask backend, they are translated to query string and sent to goodread. The result of query will be listed by revelance that are defined by goodread algorithms.
3. When user click on any book on the list, book detail will be displayed in term of isnb, title, author, publish year, average rating and rating counts.
4. If detail of that particular book has not been viewed before, Flask backend will query detail of that book from goodread and store query result in database
5. User can give a review and rating to a book. If user has left a review, any more submission of review will not be updated on the site. Also, average ratings will be caculated and displayed.
# Demo

