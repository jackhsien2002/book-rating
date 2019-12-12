import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
KEY = "u0lC95Zxu3T3dwPdGcvlA";


def main():
    error_message = "fail books shown by isbn"
    f = open("books.csv")
    #skip the header
    next(f)
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        try:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn" : isbn , "title" : title, "author" : author, "year" : year})
            print(f"{isbn} success")
        except:
            error_message += f"{isbn}\n"
    db.commit()
    print("complete table commit====")
    print(error_message)


if __name__ == "__main__":
    main()
