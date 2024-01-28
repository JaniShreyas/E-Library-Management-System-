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
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{os.path.join(currentDirectory, "database.sqlite3")}'
app.config["SECRET_KEY"] = "thisissecret"

db = SQLAlchemy()
login_manager = LoginManager(app)

db.init_app(app)
app.app_context().push()


class UserModel(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class InfoModel(db.Model):
    __tablename__ = "info"
    username = db.Column(db.String(30), db.ForeignKey("user.username"), primary_key=True)
    first_name = db.Column(db.String(30), nullable=False)
    last_name = db.Column(db.String(30))
    role = db.Column(db.String(30), nullable=False)

class SectionModel(db.Model):
    __tablename__ = "section"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(100), nullable=False)

class BookModel(db.Model):
    __tablename__ = 'book'
    isbn = db.Column(db.String(13), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)

class BookAuthorsModel(db.Model):
    __tablename__ = 'book_authors'
    isbn = db.Column(db.String(13), db.ForeignKey('book.isbn'), primary_key=True)
    author_name = db.Column(db.String(30), primary_key = True)

class BookRequestsModel(db.Model):
    __tablename__ = 'book_requests'
    isbn = db.Column(db.String(13), db.ForeignKey('book.isbn'), primary_key=True)
    username = db.Column(db.String(30), db.ForeignKey('user.username'), primary_key=True)
    request_date = db.Column(db.DateTime, nullable=False)

class BookIssueModel(db.Model):
    __tablename__ = 'book_issue'
    isbn = db.Column(db.String(13), db.ForeignKey('book.isbn'), primary_key=True)
    username = db.Column(db.String(30), db.ForeignKey('user.username'), primary_key=True)
    date_of_issue = db.Column(db.DateTime, nullable=False)
    date_of_return = db.Column(db.DateTime, nullable=False)

parser = reqparse.RequestParser()
parser.add_argument("first_name", type=str)
parser.add_argument("last_name", type=str)

parser.add_argument("username", type=str)
parser.add_argument("password", type=str)
parser.add_argument("role", type=str)

parser.add_argument("isbn", type=str)
parser.add_argument("book_name", type=str)
parser.add_argument("section_name", type=str)
parser.add_argument("description", type=str)
parser.add_argument("content", type=str)

parser.add_argument("author_names", type=str)


def check_role(role: str):
    def decorator(function):
        def wrapper(*args, **kwargs):
            info = InfoModel.query.filter_by(username=current_user.username).first()

            if not info or info.role != role:
                return {"message": f"Only {role} can access this endpoint"}, 400
            else:
                return function(*args, **kwargs)

        return wrapper

    return decorator


@login_manager.user_loader
def load_user(id):
    return UserModel.query.get(id)

class AddUser(Resource):
    def post(self):
        args = parser.parse_args()
        try:
            first_name = args["first_name"]
            last_name = args["last_name"]
            username = args["username"]
            password = args["password"]
            role = args["role"]

            if role not in ["Librarian", "General"]:
                return {"message": "Role must be either Librarian or General"}, 400

            user = UserModel(username=username, password=password)  # type: ignore
            db.session.add(user)

            info = InfoModel(username=user.username, first_name=first_name, last_name=last_name, role=role)  # type: ignore
            db.session.add(info)
            db.session.commit()

            return {"message": f"{role} user added successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500


class Login(Resource):
    def post(self):
        args = parser.parse_args()
        try:
            username = args["username"]
            password = args["password"]
            role = args["role"]

            if role not in ["Librarian", "General"]:
                return {"message": "Role must be either Librarian or General"}, 400

            this_user = UserModel.query.filter_by(username=username).first()

            if this_user:
                # User exists
                info = InfoModel.query.filter_by(username=this_user.username).first()

                if not info:
                    return {"message": "Info does not exist"}, 404

                if info.role != role:
                    return {"message": f"User is not a {role} user"}, 400

                if this_user.password == password:
                    # Password matches
                    login_user(this_user)
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
        user = UserModel.query.filter_by(username=current_user.username).first()

        if not user:
            return {"message": "User does not exist"}, 404

        info = InfoModel.query.filter_by(username=user.username).first()

        if not info:
            return {"message": "User does not exist"}, 404

        return {"username": user.username, "password": user.password, "first_name": info.first_name, "last_name": info.last_name, "role": info.role}, 200


class Logout(Resource):
    def get(self):
        logout_user()
        return {"message": "Logout successful"}, 200
    
class AddSection(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        args = parser.parse_args()
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
            args = parser.parse_args()
            isbn = args["isbn"]
            book_name = args["book_name"]
            section_name = args["section_name"]
            content = args["content"]
            author_names: str = args["author_names"]
            author_names_list: List[str] = author_names.split(",")

            section = SectionModel.query.filter_by(name=section_name).first()

            if not section:
                return {"message": "Section does not exist"}, 404
            
            book = BookModel.query.filter_by(isbn=isbn).first()

            if book:
                return {"message": "Book already exists"}, 400
            
            book = BookModel(isbn=isbn, name=book_name, content=content, section_id=section.id)  # type: ignore
            db.session.add(book)

            for author_name in author_names_list:
                author = BookAuthorsModel(isbn=isbn, author_name=author_name)  # type: ignore
                db.session.add(author)
                db.session.commit()

            return {"message": f"Book {book_name} with authors {author_names} added successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500

class ViewSections(Resource):
    @login_required
    def get(self):
        try:
            sections = SectionModel.query.all()

            if not sections:
                return {"message": "No sections exist"}, 404

            return {"sections": [section.name for section in sections]}, 200

        except Exception as e:
            return {"Error": f"{e}"}, 500

class ViewBooks(Resource):
    @login_required
    def get(self):
        try:
            books = BookModel.query.all()

            if not books:
                return {"message": "No book exists"}, 404
            
            book_sections = []
            for book in books:
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section does not exist"}, 404
                
                book_sections.append((book.name, section.name))

            return {"books": [book_section for book_section in book_sections]}, 200
        
        except Exception as e:
            return {"Error": f"{e}"}, 500

class RequestBook(Resource):
    @login_required
    @check_role(role = "General")
    def post(self):
        args = parser.parse_args()
        try:
            isbn = args["isbn"]
            book = BookModel.query.filter_by(isbn=isbn).first()

            if not book:
                return {"message": "Book does not exist"}, 404
            
            book_request = BookRequestsModel(isbn=isbn, username=current_user.username, request_date=datetime.now())  # type: ignore
            db.session.add(book_request)
            db.session.commit()

            return {"message": f"Book {book.name} requested successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500
        
class IssueBook(Resource):
    @login_required
    @check_role(role = "Librarian")
    def post(self):
        args = parser.parse_args()
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

            return {"message": f"Book {isbn} issued to {username} successfully"}, 201

        except Exception as e:
            return {"Error": f"{e}"}, 500
    
class ReturnBook(Resource):
    @login_required
    @check_role(role = "General")
    def post(self):
        args = parser.parse_args()
        try:
            isbn = args["isbn"]
            username = current_user.username
            book_issue = BookIssueModel.query.filter_by(isbn = isbn, username = username)
            
            if not book_issue:
                return {"message": f"Book with isbn {isbn} is not issued by user {username}"}, 404
            
            BookIssueModel.query.filter_by(isbn = isbn, username = username).delete()
            db.session.commit()

            return {"message": f"Book with isbn {isbn} has been returned"}, 200
        
        except Exception as e:
            return {"Error": f"{e}"}, 500

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

if __name__ == "__main__":
    app.run(debug=True)
