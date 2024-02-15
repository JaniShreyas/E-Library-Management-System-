from sqlalchemy import Integer, String,Column, ForeignKey, DateTime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Models
class UserLoginModel(db.Model, UserMixin):
    __tablename__ = "user_login"
    id = Column(Integer, primary_key=True)
    username = Column(String(40), unique=True, nullable=False)
    password = Column(String(80), nullable=False)

class UserInfoModel(db.Model):
    __tablename__ = "user_info"
    username = Column(String(40), ForeignKey("user_login.username"), primary_key=True)
    first_name = Column(String(20), nullable=False)
    last_name = Column(String(20))
    role = Column(String(20), nullable=False)

class SectionModel(db.Model):
    __tablename__ = "section"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    date_created = Column(DateTime, nullable=False)
    description = Column(String(100), nullable=False)

class BookModel(db.Model):
    __tablename__ = "book"
    isbn = Column(String(13), primary_key=True)
    name = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable = False)
    content = Column(String, nullable=False)
    section_id = Column(Integer, ForeignKey("section.id"), nullable=False)
    publisher = Column(String(100), nullable = False)

class BookAuthorModel(db.Model):
    __tablename__ = "book_author"
    isbn = Column(String(13), ForeignKey("book.isbn"), primary_key=True)
    author_name = Column(String(40), primary_key = True)

class BookRequestsModel(db.Model):
    __tablename__ = "book_request"
    isbn = Column(String(13), ForeignKey("book.isbn"), primary_key=True)
    username = Column(String(40), ForeignKey('user_login.username'), primary_key=True)
    date_of_request = Column(DateTime, nullable=False)

class BookIssueModel(db.Model):
    __tablename__ = "book_issue"
    isbn = Column(String(13), ForeignKey("book.isbn"), primary_key=True)
    username = Column(String(40), ForeignKey("user_login.username"), primary_key=True)
    date_of_issue = Column(DateTime, nullable=False)
    date_of_return = Column(DateTime, nullable=False)

class BookFeedbackModel(db.Model):
    __tablename__ = "book_feedback"
    username = Column(String(40), ForeignKey("user_login.username"), primary_key = True)
    isbn = Column(String(13), ForeignKey("book.isbn"), primary_key = True)
    feedback = Column(String(500), nullable = False)

