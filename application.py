import os
import requests
from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import xml.etree.ElementTree as ET

app = Flask(__name__)
app.config['DEBUG'] = True


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#google_api_key
KEY = "u0lC95Zxu3T3dwPdGcvlA";

@app.route("/")
def homePage():
	return render_template("index.html")

@app.route("/search", methods = ["POST", "GET"])
def searchBook():
	return render_template("search.html", username = session["username"])

@app.route("/result", methods = ["POST"])
def bookSearchResult():
	query_string=""

	isbn = request.form.get("isbn")
	if isbn != None:
		query_string += isbn + " "

	author = request.form.get("author")
	if author != None:
		query_string += author + " "

	title = request.form.get("title")
	if title != None:
		query_string += title + " "

	query_string = query_string[:-1]
	url = "https://www.goodreads.com/search/index.xml"
	books = findBook(url, query_string)

	return render_template("result.html", books = books, username = session["username"])

def findBook(url, q):
	url =f"https://www.goodreads.com/search/index.xml"
	response = requests.get(url, params = {"key" : KEY, "q" : q})
	root = ET.fromstring(response.content)
	result = root[1][6]
	books = [];
	try:
		for book in result:
			book_id_api = book[8][0].text
			book_title = book[8][1].text
			author = book[8][2][1].text
			average_rating = book[7].text
			books.append({"book_id_api" : book_id_api, "title" : book_title, "author" : author, "average_rating" : average_rating})
		return books
	except:
		books = None
		return books

@app.route("/book_detail/<int:id_api>", methods = ["GET", "POST"])
def bookDetail(id_api):

	book = db.execute("SELECT * FROM books WHERE id_api=:id_api",
				{"id_api" : id_api}).fetchone()

	#if book does not have id in data base
	if book is None:
		#update lacking data to data base
		#store column (isbn, title, author, year, id_api, work_rating_count, average_rating) 
		url = "https://www.goodreads.com/book/show.xml?key="
		response = requests.get(url, params = {"key" : KEY, "id" : id_api})
		root = ET.fromstring(response.content)
		#getting book_node at xml
		book_node = root.find("book")
		#parsing information
		isbn = book_node.find("isbn").text
		title = book_node.find("title").text
		author = book_node.find("authors").find("author").find("name").text
		year = book_node.find("publication_year").text
		if year is None:
			year = book_node.find("work").find("original_publication_year").text
		average_rating = book_node.find("average_rating").text
		work_rating_count = book_node.find("work").find("ratings_count").text
		#convert book information into dcitionary
		book_info = {"isbn" : isbn,
					"title" : title, 
	            	"author" : author,
	            	"year" : int(year), 
	            	"id_api" : int(id_api),
	            	"work_rating_count" : int(work_rating_count), 
	            	"average_rating" : float(average_rating)}

		#query data with isbn, see if book exists
		book = db.execute("SELECT * FROM books WHERE isbn=:isbn",
				{"isbn" : isbn}).fetchone()
		#if book contains isbn
		if book != None:
			#update the database
			db.execute(
				"UPDATE books SET isbn=:isbn, title=:title, author=:author, year=:year, id_api=:id_api, work_rating_count=:work_rating_count, average_rating=:average_rating WHERE isbn=:isbn"
				, book_info)
		else:
			db.execute(
				"INSERT INTO books (isbn, title, author, year, id_api, work_rating_count, average_rating) VALUES (:isbn, :title, :author, :year, :id_api, :work_rating_count, :average_rating)",
	            book_info)
		db.commit()

	if request.method == "POST":
		user_id = session["user_id"]
		book_ids = db.execute(
						"SELECT id FROM books WHERE id_api=:id_api",
						{"id_api" : id_api}
					).fetchone()
		book_id = book_ids[0]

		if not isUserWriteReview(book_id, user_id):	

			review = request.form.get("review")
			rating =request.form.get("rating")

			sql_command = "INSERT INTO reviews (review, rating, book_id, user_id) VALUES (:review, :rating, :book_id, :user_id)"
			sql_parameters = {"review" : review,
							  "rating" : rating,
							  "book_id" : book_id,
							  "user_id" : user_id}
			db.execute(sql_command, sql_parameters)
			db.commit()

			mean_review_rating = getMeanReviewRating(book_id)
			updateMeanRating(book_id, mean_review_rating)

	book = db.execute("SELECT * FROM books WHERE id_api=:id_api",
			{"id_api" : id_api}).fetchone()
	users_review = getBookReview(book.id)
	return render_template("book_detail.html", 
							book = book, 
							username = session["username"], 
							users_review = users_review
							)

def getBookReview(book_id):
	'''given book id, retrieve its user review, rating
	'''
	sql_command = "SELECT * FROM users JOIN reviews ON reviews.user_id=users.id WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}
	users = db.execute(sql_command, sql_parameters).fetchall()
	return users

def isUserWriteReview(book_id, user_id):
	sql_command = "SELECT * FROM reviews WHERE book_id=:book_id AND user_id=:user_id"
	sql_parameters = {"book_id" : book_id, "user_id" : user_id}
	review = db.execute(sql_command, sql_parameters).fetchone()
	if review == None:
		return False
	else:
		return True
def getMeanReviewRating(book_id):
	sql_command = "SELECT rating FROM reviews WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}
	reviews = db.execute(sql_command, sql_parameters).fetchall()
	count = len(reviews)

	total = 0
	for review in reviews:
		total += review.rating
	return total/count

def updateMeanRating(book_id, mean_review_rating):
	sql_command = "UPDATE books SET mean_review_rating=:mean_review_rating WHERE id=:book_id"
	sql_parameters = {"mean_review_rating" : mean_review_rating,
					  "book_id" : book_id}
	db.execute(sql_command, sql_parameters)
	db.commit()

@app.route("/login", methods = ["POST", "GET"])
def loginPage():
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
			return render_template("search.html", username = session["username"])							
		else:
			return render_template("login.html", error_message = error_message)

def getUserId(username):
	sql_command = "SELECT * FROM users WHERE username=:username"
	sql_parameters = {"username" : username}
	user = db.execute(sql_command, sql_parameters).fetchone()
	return user.id


def isUserExist(username, password):
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
	session["username"] = None
	session["user_id"] = None
	return render_template("logout.html")


@app.route("/signup", methods=["GET"])
def signUp():	
	return render_template("sign.html")

@app.route("/create", methods=["POST"])
def create():
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


