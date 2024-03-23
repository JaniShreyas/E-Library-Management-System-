from enum import auto
from sqlalchemy import Integer, String, Column, ForeignKey, DateTime
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
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), nullable=False)
    date_created = Column(DateTime, nullable=False)
    description = Column(String(100), nullable=False)


class BookModel(db.Model):
    __tablename__ = "book"
    id = Column(Integer, primary_key=True, autoincrement=True)
    isbn = Column(String(13), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    page_count = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    publisher = Column(String(100), nullable=False)
    volume = Column(Integer, nullable = False)
    section_id = Column(Integer, ForeignKey("section.id"), nullable=False)


class BookAuthorModel(db.Model):
    __tablename__ = "book_author"
    book_id = Column(Integer, ForeignKey("book.id"), primary_key=True)
    author_name = Column(String(40), primary_key=True)


class BookRequestsModel(db.Model):
    __tablename__ = "book_request"
    book_id = Column(Integer, ForeignKey("book.id"), primary_key=True)
    username = Column(String(40), ForeignKey("user_login.username"), primary_key=True)
    date_of_request = Column(DateTime, nullable=False)
    issue_time = Column(Integer, nullable=False)


class BookIssueModel(db.Model):
    __tablename__ = "book_issue"
    book_id = Column(Integer, ForeignKey("book.id"), primary_key=True)
    username = Column(String(40), ForeignKey("user_login.username"), primary_key=True)
    date_of_issue = Column(DateTime, nullable=False)
    date_of_return = Column(DateTime, nullable=False)


class BookFeedbackModel(db.Model):
    __tablename__ = "book_feedback"
    username = Column(String(40), ForeignKey("user_login.username"), primary_key=True)
    book_id = Column(Integer, ForeignKey("book.id"), primary_key=True)
    feedback = Column(String(500), nullable=False)
