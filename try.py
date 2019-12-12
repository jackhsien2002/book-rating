import requests
import os
from flask import request
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import xml.etree.ElementTree as ET

if not os.getenv("DATABASE_URL"):
	raise RuntimeError("DATABASE_URL is not set")
# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
KEY = "u0lC95Zxu3T3dwPdGcvlA";

def getNodeInXML():
	id = 375802
	url = "https://www.goodreads.com/book/show.xml?key="
	response = requests.get(url, params = {"key" : KEY, "id" : id})
	root = ET.fromstring(response.content)
	title = root.find("book").find("title").text
	print (f"book title is {title}")

def getBookById(id_api):
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
	            	"year" : year, 
	            	"id_api" : id_api,
	            	"work_rating_count" : work_rating_count, 
	            	"average_rating" : average_rating}

		#query data with isbn, see if book exists
		book = db.execute("SELECT * FROM books WHERE isbn=:isbn",
				{"isbn" : isbn}).fetchone()
		#if book contains isbn
		if book != None:
			#update the database
			db.execute(
				"UPDATE books SET title=:title, author=:author, year=:year, id_api=:id_api, work_rating_count=:work_rating_count, average_rating=:average_rating WHERE isbn=:isbn",
				book_info)
		else:
			db.execute(
				"INSERT INTO books (isbn, title, author, year, id_api, work_rating_count, average_rating) VALUES (:isbn, :title, :author, :year, :id_api, :work_rating_count, :average_rating",
	            book_info)
		db.commit()
		book = db.execute("SELECT * FROM books WHERE id_api=:id_api",
				{"id_api" : id_api}).fetchone()
	return book

def testGetBookById():
	#test not exist book
	testID1 = 5303373	
	book1 = getBookById(testID1)
	#test exist book
	testID2 = 5303373
	book2 = getBookById(testID2)
	print(f"expect not exist book \"The Chosen One\", get {book1.title}")
	print(f"expect exist book \"The Chosen One\", get {book2.title}")
def getISBNChildNodeWithKey(id):
	url = "https://www.goodreads.com/book/show.xml?key="
	response = requests.get(url, params = {"key" : KEY, "id" : id})
	root = ET.fromstring(response.content)
	isbn = root.find("book").find("isbn").text
	return isbn

def testGetISBNChildNodeWithKey():
	id = 375802
	isbn = getISBNChildNodeWithKey(id)
	print(f"book {id}, expect isbn 0812550706, actual {isbn }")

def getGoodReadAPI(isbn):
	res = requests.get("https://www.goodreads.com/book/review_counts.json", 
								#API key for developer
						params = {"key" : KEY , "isbns" : isbn})
	try:
		result = res.json()["books"]
		average_rating = result[0]["average_rating"]
		work_ratings_count = result[0]["work_ratings_count"]
		print(f"average_rating: {average_rating}")
		print(f"work_ratings_count: {work_ratings_count}")
		#print(result)
	except:
		print("book does not exist")

def testGetGoodReadAPI():
	isbn = "1632168146"
	wrong_isbn = "978163216814"
	#book = {"author" : None, "book_title" : None, "isbn" : isbn}
	book = {"author" : None, "book_title" : None, "isbn" : isbn}
	getGoodReadAPI(book["isbn"])

def getSQLdata(username, password):
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
	return is_exist

def queryUserId(username):
	sql_command = "SELECT * FROM users WHERE username=:username"
	sql_parameters = {"username" : username}
	query_user = db.execute(sql_command, sql_parameters).fetchone()
	return query_user

def testQueryUserId():
	username = "Jack"
	user = queryUserId(username)
	print(f"expect username Jack, actual {user[1]}")
	print(f"expect user id 1, actual {user[0]}")
	print(f"expect username Jack, actual {user.username}")
	print(f"expect user id 1, actual {user.id}")

def testGetSQLData():
	username1 = "Peter"
	password1 = "peterpassword"
	username2 = "Mario"
	password2 = "wrongpassword"

	result1 = getSQLdata(username1, password1)	
	result2 = getSQLdata(username2, password2)

	print(f"user {username1} is {result1}")
	print(f"user {username2} is {result2}")

def findBook(q):
	url =f"https://www.goodreads.com/search/index.xml"#?key={KEY}&q={book_name}"
	response = requests.get(url, params = {"key" : KEY, "q" : q})
	root = ET.fromstring(response.content)
	result = root[1][6]
	print(result.tag)#expect results
	for work in result:
		book_title = work[8][1].text
		author = work[8][2][1].text
		average_rating = work[7].text
		message = f"{book_title} \n\tis written by {author}, rating: {average_rating}"
		print("\n" + message + "\n")

def testFindBook():
	q1 = "harry potter"
	#q2 = "jk rowling"
	findBook(q1)
	#findBook(q2)

def getBookReview(book_id):
	'''given book id, retrieve its user review, rating
	'''
	sql_command = "SELECT * FROM users JOIN reviews ON reviews.user_id=users.id WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}
	users = db.execute(sql_command, sql_parameters).fetchall()
	return users

def testGetBookReview():
	book_id = 1
	users = getBookReview(book_id)
	book_title = db.execute("SELECT title FROM books WHERE id=:book_id", {"book_id" : book_id})
	print(f"review for book {book_title}")
	for user in users:
		print(f"user {user.username} leave a review:")
		print(f"{user.review}")
		print(f"it's rating {user.rating}")

def isUserWriteReview(book_id, user_id):
	sql_command = "SELECT * FROM reviews WHERE book_id=:book_id AND user_id=:user_id"
	sql_parameters = {"book_id" : book_id, "user_id" : user_id}
	review = db.execute(sql_command, sql_parameters).fetchone()
	if review == None:
		return False
	else:
		return True

def testIsUserWriteReview():
	book_id = 1
	user1_id = 1
	user2_id = 3
	actual1 = isUserWriteReview(book_id, user1_id)
	actual2 = isUserWriteReview(book_id, user2_id)
	print(f"expect user 1 write review true, actual {actual1}")
	print(f"expect user 2 write review false, actual {actual2}")
def getMeanReviewRating(book_id):
	sql_command = "SELECT rating FROM reviews WHERE book_id=:book_id"
	sql_parameters = {"book_id" : book_id}
	reviews = db.execute(sql_command, sql_parameters).fetchall()
	count = len(reviews)

	total = 0
	for review in reviews:
		total += review.rating
	return total/count

def testGetMeanReviewRating():
	book_id = 1
	mean_rating = getMeanReviewRating(1)
	print(f"mean rating: {mean_rating}")

def updateMeanRating(book_id, mean_review_rating):
	sql_command = "UPDATE books SET mean_review_rating=:mean_review_rating WHERE id=:book_id"
	sql_parameters = {"mean_review_rating" : mean_review_rating,
					  "book_id" : book_id}
	db.execute(sql_command, sql_parameters)
	db.commit()
	
def testUpdateMeanRating():
	book_id = 1
	mean_rating = getMeanReviewRating(book_id)
	updateMeanRating(book_id, mean_rating)
	book = db.execute("SELECT mean_review_rating FROM books WHERE id=:book_id", {"book_id" : book_id}).fetchone()
	print(f"expect mean rating: {mean_rating}, acutal rating is {book.mean_review_rating}")

def main():
	#testGetGoodReadAPI()
	#testFindBook()
	#testGetSQLData()
	#testGetISBNChildNodeWithKey()
	#testGetBookById()
	#getNodeInXML()
	#testQueryUserId()
	#testGetBookReview()
	#testIsUserWriteReview()
	#test()
	#testGetMeanReviewRating()
	testUpdateMeanRating()
if __name__ == "__main__":
	main()