import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import csv
DATABASE_URL = os.getenv("DATABASE_URL")
#alchemy object that build connection to database
engine = create_engine(DATABASE_URL)
#screate scope session for user to avoid their interactions                                                    
db = scoped_session(sessionmaker(bind=engine))
#open file
f = open("importuser.csv")
#read the file
reader = csv.reader(f)
#for every line of the file read in column
for userName, passWord, age in reader:
	#set SQL command, prepare column data in proper format
	db.execute("INSERT INTO users (username, password, age) Values(:username, :password, :age)",
				{"username" : userName, "password" : passWord, "age" : age})
	#inform that user is added
	print(f"Add User: {userName}, password: {passWord}, age: {age}")
#
db.commit()
