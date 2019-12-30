import os
import settings
import requests
from flask import Flask, session, render_template, request, jsonify
from flask import redirect, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import xml.etree.ElementTree as ET
from celery_worker import make_celery 
import time
import json
import pdb

app = Flask(__name__)
#app.config['DEBUG'] = True
app.config.update(
	DEBUG = True,
	CELERY_BROKER_URL='redis://localhost:6379',
	CELERY_RESULT_BACKEND='redis://localhost:6379'
)

celery = make_celery(app)



# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem. Every users have their own session which would not be interfered by others
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#google_api_key
KEY = os.getenv("GOOD_READ_API_KEY");

@app.route("/")
def homePage():
	return render_template("index.html")

@app.route("/search", methods = ["POST", "GET"])
def searchBook():
	return render_template("search.html", username = session["username"])

books = []
increment = 4
@app.route("/result", methods = ["POST"])
def bookSearchResult():
	query_string=""
	#concatenate the three search fields, isbn, author, title, into a query_string. These fields are seperated by space.
	isbn = request.form.get("isbn", "")
	author = request.form.get("author", "")
	title = request.form.get("title", "")
	query_list = [isbn, author, title]
	query_string = " ".join(query_list)

	#using goodreads search API to search for the books we want
	global books 
	books = findBook("https://www.goodreads.com/search/index.xml", query_string)
	
	return render_template("result.html", books = books, username = session["username"])

@app.route("/addBook", methods = ["POST"])
def addBook():
	'''
	given start and end as integer, return object that corresponding to index
	'''

	start = int(request.form.get('start'))
	end = int(request.form.get('end'))
	print('debugging================================')
	print('add book from', start, 'to', end)
	global books
	result = books[start:end]

	return jsonify(result)

def findBook(url, q):
	'''
	given a goodread url as string and a q as query string
	return a list of book dictionary. every book in the list has information of id, title, author and average rating

	When flask backend send a request to goodread, it responds with xml objects. 
	Here, we use element tree, which is like dictionary, to parse the xml. 
	Every tag in xml corresponds to a node in the element tree, and we can retrieve the value of the tags by using key of the node.
	'''
	response = requests.get(url, params = {"key" : KEY, "q" : q})
	root = ET.fromstring(response.content)
	#all books that match search result locate at index-1 at level-1 and index-6 at level-2
	result = root[1][6]
	books = [];
	try:
		#retrieve detail of books
		for book in result:
			book_id_api = book[8][0].text
			book_title = book[8][1].text
			author = book[8][2][1].text
			average_rating = book[7].text
			books.append({
				"book_id_api" : book_id_api,
				"title" : book_title, 
				"author" : author, 
				"average_rating" : average_rating
			})
		return books
	except:
		books = None
		return books


def write_book_to_database(book_info):
	sql_command = "INSERT INTO books (isbn, title, author, year, id_api, work_rating_count, average_rating)\
					 VALUES (:isbn, :title, :author, :year, :id_api, :work_rating_count, :average_rating)"
	db.execute(
		sql_command,
        book_info
	)
	db.commit()

@app.route("/book_detail/<int:id_api>", methods = ["GET", "POST"])
def bookDetail(id_api):
	'''
	given a book id as integer, send a request to goodread
	'''
	#query book from database according to book's id_api
	book = db.execute("SELECT * FROM books WHERE id_api=:id_api", {"id_api" : id_api}).fetchone()

	#if book does not exist in database
	if book is None:
		#update data to data base
		##store column (isbn, title, author, year, id_api, work_rating_count, average_rating) 
		url = "https://www.goodreads.com/book/show.xml"
		response = requests.get(url, params = {"key" : KEY, "id" : id_api})
		print (response)

		root = ET.fromstring(response.content)
		book_node = root.find("book")
		book = parseDetailFromBookNode(book_node, id_api)
		#invoke celery to work on writing book details to database
		write_book_to_database(book)

	#if user submit a review for the book
	if request.method == "POST":
		#if user does not leave review before
		user_id = session["user_id"]		
		if not isUserWriteReview(id_api, user_id):	
			#retrieve user input
			review = request.form.get("review")
			rating =request.form.get("rating")
			#update database with user's review on the book
			sql_command = "INSERT INTO reviews (review, rating, book_id, user_id) \
							VALUES (:review, :rating, :book_id, :user_id)"
			sql_parameters = {
				"review" : review,
				"rating" : rating,
				"book_id" : id_api,
				"user_id" : user_id
			}
			db.execute(sql_command, sql_parameters)
			db.commit()
			#calcualte rating of the book right after user submit rating
			mean_review_rating = getMeanReviewRating(id_api)
			#update the rating to databse and get the newest book object from database
			book = updateMeanRating(id_api, mean_review_rating)

	#retrieve all the reviews on a given book
	users_in_reviews = getBookReview(id_api)

	return render_template("book_detail.html", 
							book = book, 
							username = session["username"], 
							users_in_reviews = users_in_reviews)

def parseDetailFromBookNode(book_node, id_api):
	'''
	given a book node and an id_api as integer, parse book detail from tree nodes
	return a book dictionary
	'''
	isbn = book_node.find("isbn").text
	title = book_node.find("title").text
	author = book_node.find("authors").find("author").find("name").text
	year = book_node.find("publication_year").text
	if year != None:
		year = int(year)
	average_rating = book_node.find("average_rating").text
	if average_rating != None:
		average_rating = float(average_rating)
	work_rating_count = book_node.find("work").find("ratings_count").text

	return {
		"isbn" : isbn,
		"title" : title, 
		"author" : author,
		"year" : year, 
		"id_api" : id_api,
		"work_rating_count" : int(work_rating_count), 
		"average_rating" : float(average_rating),
		"mean_review_rating" : None
	}

def getBookReview(book_id):
	'''
	given book id as integer, retrieve users in the book reviews.
	'''
	#argument must be integer
	assert isinstance(book_id, int)

	#prepare sql command for SQLAlchemy
	sql_command = "SELECT * FROM users JOIN reviews ON reviews.user_id=users.id WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}

	#query all uses' reviews from database
	users_in_reviews = db.execute(sql_command, sql_parameters).fetchall()

	return users_in_reviews

def isUserWriteReview(book_id, user_id):
	'''
	if user write book review before, return True; If not, return False
	'''
	sql_command = "SELECT * FROM reviews WHERE book_id=:book_id AND user_id=:user_id"
	sql_parameters = {"book_id" : book_id, "user_id" : user_id}
	review = db.execute(sql_command, sql_parameters).fetchone()
	if review == None:
		return False
	else:
		return True

def getMeanReviewRating(book_id):
	'''
	given a book id as integer, average all the ratings of a book
	return average rating of book
	'''
	sql_command = "SELECT rating FROM reviews WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}
	reviews = db.execute(sql_command, sql_parameters).fetchall()
	count = len(reviews)

	total = 0
	for review in reviews:
		total += review.rating
	return total/count

def updateMeanRating(book_id, mean_review_rating):
	'''
	given book_id and mean_review_rating as integer, update book object in database
	return book object that is updated
	'''
	sql_command = "UPDATE books SET mean_review_rating=:mean_review_rating WHERE id_api=:book_id"
	sql_parameters = {
		"mean_review_rating" : mean_review_rating,
		"book_id" : book_id
	}
	db.execute(sql_command, sql_parameters)
	db.commit()

	sql_command = "SELECT * FROM books WHERE id_api=:book_id"
	sql_parameters = {'book_id' : book_id}
	book = db.execute(sql_command, sql_parameters).fetchone()
	return book


@app.route("/login", methods = ["POST", "GET"])
def loginPage():
	'''
	at loginPage view, user will be prompted with username and password field.
	after user type valid user information, they will login to application
	'''
	if request.method == "GET":	
		return render_template("login.html")
	elif session.get("username", None) != None:
		error_message = "please log out your account"
		return render_template("login.html", error_message = error_message)
	else:
		username = request.form.get("username")
		password = request.form.get("password")
		is_exist, error_message = isUserExist(username, password)
		if is_exist:			
			session["username"] = username
			session["user_id"] = getUserId(username)
			return redirect(url_for('searchBook'))							
		else:
			return render_template("login.html", error_message = error_message)

def getUserId(username):
	'''
	given username as string, query user information from database
	return user id
	'''
	sql_command = "SELECT * FROM users WHERE username=:username"
	sql_parameters = {"username" : username}
	user = db.execute(sql_command, sql_parameters).fetchone()
	return user.id


def isUserExist(username, password):
	'''
	given username and password as string
	return True if user data is in database; else return False
	'''
	person = db.execute("SELECT * FROM users WHERE username=:username AND password=:password",
				{"username" : username, "password" : password}).fetchall()
	error_message = ""
	is_exist = False
	if (len(person) == 0):
		error_message = "user does not exist"
	elif (len(person) == 1):
		is_exist = True		
	else:
		error_message = "Username is duplicated or some error occur when data is query from database"
	return is_exist, error_message

@app.route("/logout", methods = ["GET"])
def logout():
	'''
	logout the user by setting user's session as None at our database
	'''
	session["username"] = None
	session["user_id"] = None
	return render_template("logout.html")


@app.route("/signup", methods=["GET"])
def signUp():
	'''
	user signup here with username and password
	'''
	return render_template("sign.html")

@app.route("/create", methods=["POST"])
def create():
	'''
	extract user's information from their signup form and create user's data at our database
	if user's information is written to database successfully,
	return create_success page, else return create_fail page
	'''
	#retrieve form username and password from request
	username = request.form.get("username")
	password = request.form.get("password")
	#register userdata in data base at heroku
	try:
		db.execute("INSERT INTO users (username, password) Values(:username, :password)",
			{"username" : username, "password" : password})
		db.commit()#if username and password exist, this line will cause error
		return render_template("create_success.html")
	except:
		message = "Sign Up fail due to duplicate username and password. Please try a new set."
		return render_template("create_fail.html")

@app.route("/api/<string:isbn>", methods=["GET"])
def getAPI(isbn):
	'''
	given isbn as string, query book from our database and return it to user in JSON format
	if book does not exist in our database, return an error page 
	'''
	sql_command = "SELECT * FROM books WHERE isbn=:isbn"
	sql_parameters = {"isbn" : isbn}
	book = db.execute(sql_command, sql_parameters).fetchone()
	if len(book) == 0:
		return render_template("error.html")
	return jsonify(
				title = book.title,
	    		author = book.author,
	    		year = book.year,
	    		isbn = book.isbn,
	    		review_count = book.work_rating_count,
	    		average_score = str(book.average_rating)
		   )


