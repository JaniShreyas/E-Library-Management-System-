from flask import Flask, request
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin, login_required
import os
from typing import List
from datetime import datetime, timedelta

currentDirectory = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
api = Api(app)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{os.path.join(currentDirectory, "db.sqlite3")}'
app.config["SECRET_KEY"] = "PsIK>@%=`TiDs$>"

db = SQLAlchemy()
login_manager = LoginManager(app)

db.init_app(app)
app.app_context().push()


# Models
class UserLoginModel(db.Model, UserMixin):
    __tablename__ = "user_login"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

class UserInfoModel(db.Model):
    __tablename__ = "user_info"
    username = db.Column(db.String(40), db.ForeignKey("user_login.username"), primary_key=True)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False)

class SectionModel(db.Model):
    __tablename__ = "section"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(100), nullable=False)

class BookModel(db.Model):
    __tablename__ = "book"
    isbn = db.Column(db.String(13), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # page_count = db.Column(db.Integer, nullable = False)
    content = db.Column(db.String(300), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"), nullable=False)

class BookAuthorModel(db.Model):
    __tablename__ = "book_author"
    isbn = db.Column(db.String(13), db.ForeignKey("book.isbn"), primary_key=True)
    author_name = db.Column(db.String(40), primary_key = True)

class BookRequestsModel(db.Model):
    __tablename__ = "book_request"
    isbn = db.Column(db.String(13), db.ForeignKey("book.isbn"), primary_key=True)
    username = db.Column(db.String(40), db.ForeignKey('user_login.username'), primary_key=True)
    date_of_request = db.Column(db.DateTime, nullable=False)

class BookIssueModel(db.Model):
    __tablename__ = "book_issue"
    isbn = db.Column(db.String(13), db.ForeignKey("book.isbn"), primary_key=True)
    username = db.Column(db.String(40), db.ForeignKey("user_login.username"), primary_key=True)
    date_of_issue = db.Column(db.DateTime, nullable=False)
    date_of_return = db.Column(db.DateTime, nullable=False)

class BookFeedbackModel(db.Model):
    __tablename__ = "book_feedback"
    username = db.Column(db.String(40), db.ForeignKey("user_login.username"), primary_key = True)
    isbn = db.Column(db.String(13), db.ForeignKey("book.isbn"), primary_key = True)
    feedback = db.Column(db.String(500), nullable = False)

# Parse Args
reqParser = reqparse.RequestParser()

reqParser.add_argument("username", type=str)
reqParser.add_argument("password", type=str)
reqParser.add_argument("first_name", type=str)
reqParser.add_argument("last_name", type=str)
reqParser.add_argument("role", type=str)

reqParser.add_argument("isbn", type=str)
reqParser.add_argument("book_name", type=str)
reqParser.add_argument("page_count", type = int)
reqParser.add_argument("section_name", type=str)
reqParser.add_argument("description", type=str)
reqParser.add_argument("content", type=str)
reqParser.add_argument("author_names", type=str)

reqParser.add_argument("feedback", type = str)
reqParser.add_argument("old_to_new_author", type = str)
reqParser.add_argument("old_to_new_isbn", type = str)

# Decorator function to verify role
def check_role(role: str):
    def decorator(function):
        def wrapper(*args, **kwargs):
            info = UserInfoModel.query.filter_by(username=current_user.username).first()

            if not info:
                return {"message": "Info not found"}, 404

            if info.role != role:
                return {"message": f"Only {role} user has access here"}, 400
            else:
                return function(*args, **kwargs)
        return wrapper
    return decorator

@login_manager.user_loader
def load_user(id):
    return UserLoginModel.query.get(id)

class AddUser(Resource):
    def post(self):
        args = reqParser.parse_args()
        try:
            username = args["username"]
            password = args["password"]
            first_name = args["first_name"]
            last_name = args["last_name"]
            role = args["role"]

            if role not in ["Librarian", "General"]:
                return {"message": "Role must be either Librarian or General"}, 400

            userLogin = UserLoginModel(username=username, password=password)  # type: ignore
            db.session.add(userLogin)

            info = UserInfoModel(username=userLogin.username, first_name=first_name, last_name=last_name, role=role)  # type: ignore
            db.session.add(info)
            db.session.commit()

            return {"message": f"{role} user added successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500


class Login(Resource):
    def post(self):
        args = reqParser.parse_args()
        try:
            username = args["username"]
            password = args["password"]
            role = args["role"]

            if role not in ["Librarian", "General"]:
                return {"message": "Role must be either Librarian or General"}, 400

            userLogin = UserLoginModel.query.filter_by(username=username).first()

            if userLogin:
                # User exists
                info = UserInfoModel.query.filter_by(username=userLogin.username).first()

                if not info:
                    return {"message": "Info does not exist"}, 404

                if info.role != role:
                    return {"message": f"User is not a {role} user"}, 400

                if userLogin.password == password:
                    # Password matches
                    login_user(userLogin)
                    return {
                        "message": f"{role} user Login successful. Welcome {info.first_name}"
                    }, 200
                else:
                    # Password does not match
                    return {"message": "Incorrect password"}, 400
            else:
                # User does not exist
                return {"message": f"{role} user does not exist"}, 404

        except Exception as e:
            return {"Error": f"{e}"}, 500

class UserInfo(Resource):
    @login_required
    def get(self):
        userLogin = UserLoginModel.query.filter_by(username=current_user.username).first()

        if not userLogin:
            return {"message": "User does not exist"}, 404

        info = UserInfoModel.query.filter_by(username=userLogin.username).first()

        if not info:
            return {"message": "User does not exist"}, 404

        last_name = info.last_name if info.last_name else ""

        return {"username": userLogin.username, "password": userLogin.password, "first_name": info.first_name, "last_name": last_name, "role": info.role}, 200


class Logout(Resource):
    def get(self):
        logout_user()
        return {"message": "Logout successful"}, 200
    
class AddSection(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            name = args["section_name"]
            description = args["description"]
            
            date_created = datetime.now()

            section = SectionModel(name=name, date_created=date_created, description=description)  # type: ignore
            db.session.add(section)
            db.session.commit()

            return {"message": f"Section {name} added successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500

class AddBookAuthor(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        try:
            args = reqParser.parse_args()
            isbn = args["isbn"]
            book_name = args["book_name"]
            section_name = args["section_name"]
            content_path = args["content"]
            author_names: str = args["author_names"]
            author_names_list: List[str] = author_names.split(",")

            section = SectionModel.query.filter_by(name=section_name).first()

            if not section:
                return {"message": "Section does not exist"}, 404
            
            book = BookModel.query.filter_by(isbn=isbn).first()

            if book:
                return {"message": "Book already exists"}, 400
            
            book = BookModel(isbn=isbn, name=book_name, content=content_path, section_id=section.id)  # type: ignore
            db.session.add(book)

            for author_name in author_names_list:
                author = BookAuthorModel(isbn=isbn, author_name=author_name)  # type: ignore
                db.session.add(author)
            db.session.commit()

            return {"message": f"Book {book_name} with authors {author_names} added successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500

class ViewSections(Resource):
    @login_required
    def get(self):
        try:
            sections = list(SectionModel.query.all())
            
            if not sections:
                return {"message": "No section exists"}, 404
            
            return {"sections": [(section.id, section.name, str(section.date_created), section.description) for section in sections]}, 200

        except Exception as e:
            return {"Error": f"{e}"}, 500

class ViewBooks(Resource):
    @login_required
    def get(self):
        try:
            books = BookModel.query.all()

            if not books:
                return {"message": "No book exists"}, 404
            
            outputList = []
            for book in books:
                section = SectionModel.query.filter_by(id = book.section_id).first()
                if not section:
                    return {"message": "Section not found"}, 404
                
                outputList.append((book.isbn, book.name, book.content, book.section_id, section.name))
            
            return {"Books": outputList}
        
        except Exception as e:
            return {"Error": f"{e}"}, 500

class RequestBook(Resource):
    @login_required
    @check_role(role = "General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            book = BookModel.query.filter_by(isbn=isbn).first()

            if not book:
                return {"message": "Book does not exist"}, 404
            
            book_request = BookRequestsModel(isbn=isbn, username=current_user.username, date_of_request=datetime.now())  # type: ignore
            db.session.add(book_request)
            db.session.commit()

            return {"message": f"Book {book.name} requested successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500
        
class IssueBook(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            username = args["username"]

            book_request = BookRequestsModel.query.filter_by(isbn=isbn, username=username).first()

            if not book_request:
                return {"message": "Book request does not exist"}, 404
            
            book_issue = BookIssueModel(isbn=isbn, username=username, date_of_issue=datetime.now(), date_of_return=datetime.now() + timedelta(days=7))  # type: ignore
            db.session.add(book_issue)

            BookRequestsModel.query.filter_by(isbn=isbn, username=username).delete()
            db.session.commit()
            
            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            return {"message": f"Book {book.name} issued to {username} successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500
    
class ReturnBook(Resource):
    @login_required
    @check_role(role = "General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            username = current_user.username
            book_issue = BookIssueModel.query.filter_by(isbn = isbn, username = username).first()
            
            if not book_issue:
                return {"message": f"Book with isbn {isbn} is not issued by user {username}"}, 404
            
            BookIssueModel.query.filter_by(isbn = isbn, username = username).delete()
            db.session.commit()

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            return {"message": f"Book {book.name} has been returned"}, 200
        
        except Exception as e:
            return {"Error": f"{e}"}, 500

class BookFeedback(Resource):
    @login_required
    @check_role(role = "General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            feedback = args["feedback"]
            
            username = current_user.username

            book_feedback = BookFeedbackModel(isbn = isbn, username = username, feedback = feedback)  # type: ignore
            db.session.add(book_feedback)
            db.session.commit()

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404
            
            return {"message": f"Feedback for {book.name} submitted successfully"}, 200

        except Exception as e:
            return {"Error": f"{e}"}, 500

class EditBookInfo(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            old_to_new_isbn = args["old_to_new_isbn"]
            name = args["book_name"]
            old_to_new_author = args["old_to_new_author"]
            # page_count = args["page_count"]
            section_name = args["section_name"]
            oldIsbn, newIsbn = tuple(old_to_new_isbn.split(','))
            oldAuthor, newAuthor = tuple(old_to_new_author.split(','))

            book = BookModel.query.filter_by(isbn = oldIsbn).first()
            if not book:
                return {"message": f"Book does not exist"}, 404
            
            book_author = BookAuthorModel.query.filter_by(isbn = oldIsbn, author_name = oldAuthor).first()
            if not book_author:
                return {"message": f"ISBN does not exist or Author {oldAuthor} does not exist"}, 404
            
            all_book_entries_in_book_author = BookAuthorModel.query.filter_by(isbn = oldIsbn).update({"isbn": newIsbn})
            
            section = SectionModel.query.filter_by(name = section_name).first()
            if not section:
                return {"message": f"Section {section_name} does not exist"}, 404
            
            book.isbn = newIsbn
            book.name = name
            book.section_id = section.id
            #book.page_count = page_count

            book_author.isbn = newIsbn
            book_author.author_name = newAuthor
            db.session.commit()

            return {"message": "Book info changed successfully"}
        
        except Exception as e:
            return {"Error": f"{e}"}


api.add_resource(AddUser, "/api/addUser")
api.add_resource(Login, "/api/login")
api.add_resource(UserInfo, "/api/userInfo")
api.add_resource(Logout, "/api/logout")
api.add_resource(AddSection, '/api/addSection')
api.add_resource(AddBookAuthor, '/api/addBookAuthor')
api.add_resource(ViewSections, '/api/viewSections')
api.add_resource(ViewBooks, '/api/viewBooks')
api.add_resource(RequestBook, '/api/requestBook')
api.add_resource(IssueBook, '/api/issueBook')
api.add_resource(ReturnBook, "/api/returnBook")
api.add_resource(BookFeedback, "/api/bookFeedback")
api.add_resource(EditBookInfo, "/api/editBookInfo")

if __name__ == "__main__":
    app.run(debug=True)
