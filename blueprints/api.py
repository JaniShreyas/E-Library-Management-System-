from distutils.command import upload
import os
from flask import Blueprint, request
from flask_restful import Resource, reqparse, Api
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from traitlets import default
from models import (
    db,
    UserLoginModel,
    UserInfoModel,
    SectionModel,
    BookModel,
    BookAuthorModel,
    BookRequestsModel,
    BookIssueModel,
    BookFeedbackModel,
)
from typing import List, Callable
from datetime import date, timedelta
import werkzeug
from werkzeug.utils import secure_filename

api_bp = Blueprint("api", __name__)
api = Api(api_bp)


# Parse Args
reqParser = reqparse.RequestParser()

reqParser.add_argument("username", type=str)
reqParser.add_argument("password", type=str)
reqParser.add_argument("first_name", type=str)
reqParser.add_argument("last_name", type=str)
reqParser.add_argument("role", type=str)

reqParser.add_argument("book_id", type=int)
reqParser.add_argument("isbn", type=str)
reqParser.add_argument("book_name", type=str)
reqParser.add_argument("page_count", type=int)
reqParser.add_argument("section_name", type=str)
reqParser.add_argument("description", type=str)
reqParser.add_argument("content", type=str)
reqParser.add_argument("publisher", type=str)
reqParser.add_argument("author_names", type=str)
reqParser.add_argument("issue_time", type=int)

reqParser.add_argument("section_id", type=int)

reqParser.add_argument("feedback", type=str)
reqParser.add_argument("rating", type=int)
reqParser.add_argument("old_to_new_author", type=str)
reqParser.add_argument("new_isbn", type=str)


addBookArg = reqparse.RequestParser()

addBookArg.add_argument("book_id", type=int, location="form")
addBookArg.add_argument("isbn", type=str, location="form")
addBookArg.add_argument("book_name", type=str, location="form")
addBookArg.add_argument("page_count", type=int, location="form")
addBookArg.add_argument("section_name", type=str, location="form")
addBookArg.add_argument("publisher", type=str, location="form")
addBookArg.add_argument("author_names", type=str, location="form")
addBookArg.add_argument("volume", type=str, location="form")
addBookArg.add_argument("price", type=str, location="form")
addBookArg.add_argument(
    "book_file", type=werkzeug.datastructures.FileStorage, location="files"
)

allowed_extensions = ["pdf"]
upload_folder = os.getcwd() + "/static/books"


def raw(input: str) -> str:
    return input.lower().replace(" ", "")


def isFileAllowed(filename: str):
    return ("." in filename) and (filename.split(".")[-1].lower() in allowed_extensions)


# Decorator function to verify role
def check_role(role: str):
    def decorator(function: Callable):
        def wrapper(*args, **kwargs):
            info = UserInfoModel.query.filter_by(uid=current_user.id).first()

            if not info:
                return {"message": "Info not found"}, 404

            if info.role != role:
                return {"message": f"Only {role} user has access here"}, 400
            else:
                return function(*args, **kwargs)

        wrapper.__name__ = function.__name__
        return wrapper

    return decorator


login_manager = LoginManager()


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

            userInfo = UserLoginModel.query.filter_by(username=username).first()
            if userInfo:
                return {"message": "Username already exists"}, 400

            if not first_name:
                return {"message": "first_name not provided"}, 400

            userLogin = UserLoginModel(username=username, password=password)  # type: ignore
            db.session.add(userLogin)
            db.session.commit()

            info = UserInfoModel(uid=userLogin.id, first_name=first_name, last_name=last_name, role="General")  # type: ignore
            db.session.add(info)
            db.session.commit()

            last_name = info.last_name if info.last_name else ""  # type: ignore

            return {
                "username": userLogin.username,
                "password": userLogin.password,
                "first_name": info.first_name,
                "last_name": last_name,
                "role": "General",
            }, 201

        except Exception as e:
            return {"error": str(e)}, 500


class Login(Resource):
    def post(self):
        args = reqParser.parse_args()
        try:
            username = args["username"]
            password = args["password"]

            userLogin = UserLoginModel.query.filter_by(username=username).first()

            if userLogin:
                # User exists
                info = UserInfoModel.query.filter_by(uid=userLogin.id).first()

                if not info:
                    return {"message": "Info does not exist"}, 404

                if userLogin.password == password:
                    # Password matches
                    login_user(userLogin)
                    return {
                        "message": f"{info.role} user Login successful. Welcome {info.first_name}"
                    }, 200
                else:
                    # Password does not match
                    return {"message": "Incorrect username or password"}, 400
            else:
                # User does not exist
                return {"message": f"User does not exist"}, 404

        except Exception as e:
            return {"error": str(e)}, 500


class UserInfo(Resource):
    @login_required
    def get(self):
        try:
            userLogin = UserLoginModel.query.filter_by(id=current_user.id).first()

            if not userLogin:
                return {"message": "User does not exist"}, 404

            info = UserInfoModel.query.filter_by(uid=userLogin.id).first()

            if not info:
                return {"message": "User does not exist"}, 404

            last_name = info.last_name if info.last_name else ""

            return {
                "username": userLogin.username,
                "password": userLogin.password,
                "first_name": info.first_name,
                "last_name": last_name,
                "role": info.role,
            }, 200

        except Exception as e:
            return {"error": str(e)}, 500


class Logout(Resource):
    def get(self):
        logout_user()
        return {"message": "Logout successful"}, 200


class AddSection(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            name = args["section_name"]
            description = args["description"]

            section = SectionModel.query.filter_by(name=name).first()
            if section:
                return {"message": f"Section {name} already exists"}, 400

            date_created = date.today()

            if not name:
                return {"message": "Name not given"}, 400

            search_word = raw(name)
            if description:
                search_word += raw(description)

            section = SectionModel(name=name, date_created=date_created, description=description, search_word=search_word)  # type: ignore
            db.session.add(section)
            db.session.commit()

            return {
                "name": section.name,
                "description": section.description,
                "date_created": str(section.date_created),
                "search_word": section.search_word,
            }, 201

        except Exception as e:
            return {"error": str(e)}, 500


class AddBook(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        try:

            file_args = addBookArg.parse_args()

            isbn = file_args["isbn"]
            book_name = file_args["book_name"]
            page_count = file_args["page_count"]
            section_name = file_args["section_name"]
            book_file = file_args["book_file"]
            publisher = file_args["publisher"]
            author_names: str = file_args["author_names"]
            author_names_list: List[str] = [
                author_name.strip() for author_name in author_names.split(",")
            ]
            volume = file_args["volume"]
            price = file_args["price"]

            section = SectionModel.query.filter_by(name=section_name).first()

            if not section:
                return {"message": "Section does not exist"}, 404

            book = BookModel.query.filter_by(isbn=isbn).first()

            if book:
                return {"message": "Book already exists"}, 400

            if not book_file:
                return {"message": "Book file not given"}

            if not book_file.filename:
                return {"message": "No file name"}, 400

            filename = secure_filename(book_file.filename)

            if not isFileAllowed(filename):
                return {"message": "This file type is not allowed"}, 400

            content_path = os.path.join(upload_folder, filename)

            if os.path.exists(content_path):
                book = BookModel.query.filter_by(content="books/" + filename).first()
                if not book:
                    return (
                        {
                            "message": "There is a book pdf which exists but there is no book with the corresponding path.\
                             Need to manually remove the pdf"
                        },
                        400,
                    )

                return {
                    "message": f"This book PDF already exists and is referenced by book_id: {book.id} with name: {book.name}"
                }, 400

            book = BookModel(isbn=isbn, name=book_name, page_count=page_count, content="books/" + filename, publisher=publisher, section_id=section.id, volume=volume, search_word="hello", price=price)  # type: ignore
            db.session.add(book)
            db.session.commit()

            for author_name in author_names_list:
                book_author = BookAuthorModel(book_id=book.id, author_name=author_name, search_word="hello")  # type: ignore
                db.session.add(book_author)
            db.session.commit()

            book_file.save(content_path)

            return {
                "message": f"Book {book_name} with authors {author_names} added successfully"
            }, 201

        except Exception as e:
            return {"error": str(e)}, 500


class ViewSections(Resource):
    @login_required
    def get(self):
        try:
            sections = list(SectionModel.query.all())

            if not sections:
                return {"message": "No section exists"}, 404

            return [
                {
                    "section_id": section.id,
                    "name": section.name,
                    "description": section.description,
                    "date_created": str(section.date_created)
                }
                for section in sections
            ], 200

        except Exception as e:
            return {"error": str(e)}, 500


class ViewBooks(Resource):
    @login_required
    def get(self):
        try:
            books = BookModel.query.all()

            if not books:
                return {"message": "No book exists"}, 404

            outputList = []
            for book in books:
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section not found"}, 404
                
                book_authors = BookAuthorModel.query.filter_by(book_id = book.id).all()

                outputList.append(
                    {
                        "id": book.id,
                        "isbn": book.isbn,
                        "name": book.name,
                        "page_count": book.page_count,
                        "content": book.content,
                        "publisher": book.publisher,
                        "section_id": book.section_id,
                        "section_name": section.name,
                        "authors": ",".join([book_author.author_name for book_author in book_authors])
                    }
                )

            return outputList

        except Exception as e:
            return {"error": str(e)}, 500


class RequestBook(Resource):
    @login_required
    @check_role(role="General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            issue_time = args["issue_time"]
            book = BookModel.query.filter_by(isbn=isbn).first()

            if issue_time > 7:
                return {"message": "Issue time cannot be greater than 7"}

            if issue_time < 1:
                return {"message": "Issue time must be greater than 0"}

            if not book:
                return {"message": "Book does not exist"}, 404

            book_request = BookRequestsModel.query.filter_by(
                book_id=book.id, uid=current_user.id
            ).first()
            if book_request:
                return {"message": "Book already requested"}, 400

            book_issue = BookIssueModel.query.filter_by(
                book_id=book.id, uid=current_user.id
            ).first()
            if book_issue:
                return {"message": "Book has already been issued"}, 400

            today = date.today()
            book_request = BookRequestsModel(book_id=book.id, uid=current_user.id, date_of_request=today, issue_time=issue_time)  # type: ignore
            db.session.add(book_request)
            db.session.commit()

            return {
                "isbn": isbn,
                "date_of_request": date.today(),
                "issue_time": today,
            }, 201

        except Exception as e:
            return {"error": str(e)}, 500


class ViewBookRequests(Resource):
    @login_required
    @check_role(role="Librarian")
    def get(self):
        try:
            book_requests = BookRequestsModel.query.all()
            return [
                {
                    "book_id": book_request.book_id,
                    "uid": book_request.uid,
                    "date_of_request": str(book_request.date_of_request),
                    "issue_time": book_request.issue_time,
                }
                for book_request in book_requests
            ]

        except Exception as e:
            return {"error": str(e)}, 500


class IssueBook(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            username = args["username"]

            user_login = UserLoginModel.query.filter_by(username=username).first()
            if not user_login:
                return {"message": "User login not found"}, 404

            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_request = BookRequestsModel.query.filter_by(
                book_id=book.id, uid=user_login.id
            ).first()

            if not book_request:
                return {"message": "Book request does not exist"}, 404

            today = date.today()
            return_date = today + timedelta(days=book_request.issue_time)
            book_issue = BookIssueModel(book_id=book.id, uid=user_login.id, date_of_issue=today, date_of_return=return_date)  # type: ignore
            db.session.add(book_issue)

            BookRequestsModel.query.filter_by(
                book_id=book.id, uid=user_login.id
            ).delete()
            db.session.commit()

            return {
                "book_id": book_issue.book_id,
                "date_of_issue": str(today),
                "date_of_return": str(return_date),
            }, 201

        except Exception as e:
            return {"error": str(e)}, 500


class ViewIssuedBooks(Resource):
    @login_required
    def get(self):
        info = UserInfoModel.query.filter_by(uid=current_user.id).first()
        if not info:
            return {"message": "User info does not exist"}, 404

        try:
            if info.role == "General":
                username = current_user.username
            else:
                username = request.args.get("username", default="testUname")

            user_login = UserLoginModel.query.filter_by(username=username).first()
            if not user_login:
                if info.role == "Librarian":
                    return {"message": "Provide username in argument"}, 400
                return {"message": "User login not found"}, 404

            book_issue = BookIssueModel.query.filter_by(uid=user_login.id).all()

            outputList = []
            for issued_book in book_issue:
                book = BookModel.query.filter_by(id=issued_book.book_id).first()
                if not book:
                    return {"message": "Book does not exist"}, 404
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section does not exist"}, 404
                
                book_authors = BookAuthorModel.query.filter_by(book_id = book.id).all()

                outputList.append(
                    {
                        "isbn": book.isbn,
                        "name": book.name,
                        "page_count": book.page_count,
                        "content": book.content,
                        "publisher": book.publisher,
                        "section_id": book.section_id,
                        "section_name": section.name,
                        "authors": ",".join([author.author_name for author in book_authors])
                    }
                )

            return outputList

        except Exception as e:
            return {"error": str(e)}


class ReturnBook(Resource):
    @login_required
    @check_role(role="General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            uid = current_user.id

            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_issue = BookIssueModel.query.filter_by(
                book_id=book.id, uid=uid
            ).first()

            user_login = UserLoginModel.query.filter_by(id=uid).first()
            if not user_login:
                return {"message": "User login not found"}, 404

            if not book_issue:
                return {
                    "message": f"Book with isbn {isbn} is not issued by user {user_login.username}"
                }, 404

            BookIssueModel.query.filter_by(book_id=book.id, uid=uid).delete()
            db.session.commit()

            return {"message": f"Book {book.name} has been returned"}, 200

        except Exception as e:
            return {"error": str(e)}, 500


class BookFeedback(Resource):
    @login_required
    @check_role(role="General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            feedback = args["feedback"]
            rating = args["rating"]

            uid = current_user.id

            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_feedback = BookFeedbackModel(book_id=book.id, uid=uid, feedback=feedback, rating=rating)  # type: ignore
            db.session.add(book_feedback)
            db.session.commit()

            return {"book_id": book.id, "feedback": feedback, "rating": rating}, 200

        except Exception as e:
            return {"error": str(e)}, 500


class ViewFeedbacks(Resource):
    @login_required
    @check_role(role="Librarian")
    def get(self):
        try:
            isbn = request.args.get("isbn", default=None)

            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            feedbacks = None
            if isbn:
                feedbacks = BookFeedbackModel.query.filter_by(book_id=book.id).all()
            else:
                feedbacks = BookFeedbackModel.query.all()

            if not feedbacks:
                return {"message": "No feedbacks of this book exist"}

            return [
                {
                    "isbn": isbn,
                    "username": feedback.uid,
                    "feedback": feedback.feedback,
                    "rating": feedback.rating,
                }
                for feedback in feedbacks
            ]

        except Exception as e:
            return {"error": str(e)}, 500


class EditBook(Resource):
    @login_required
    @check_role(role="Librarian")
    def put(self):
        file_args = addBookArg.parse_args()
        try:

            book_id = file_args["book_id"]
            isbn = file_args["isbn"]
            name = file_args["book_name"]
            page_count = file_args["page_count"]
            section_name = file_args["section_name"]
            book_file = file_args["book_file"]
            publisher = file_args["publisher"]
            authors: str = file_args["author_names"]

            volume = file_args["volume"]
            price = file_args["price"]

            content_path = None
            if book_file:
                if book_file.filename:
                    filename = secure_filename(book_file.filename)

                    if not isFileAllowed(filename):
                        return {"message": "This file type is not allowed"}, 400

                    content_path = os.path.join(upload_folder, filename)

                    if os.path.exists(content_path):
                        book = BookModel.query.filter_by(
                            content="books/" + filename
                        ).first()
                        if not book:
                            return (
                                {
                                    "message": "There is a book pdf which exists but there is no book with the corresponding path.\
                                    Need to manually remove the pdf"
                                },
                                500,
                            )

                        return {
                            "message": f"This book PDF already exists and is referenced by book_id: {book.id} with name: {book.name}"
                        }, 400

            try:
                if page_count:
                    page_count = int(page_count)
                    if page_count < 1:
                        return {"message": "Page count must be a positive integer"}, 400
            except:
                return {"message": "Page count should be an integer"}, 400

            if not book_id:
                return {"message": "Book id not given"}, 400

            book = BookModel.query.filter_by(id=book_id).first()
            if not book:
                return {"message": "Book does not exist"}, 400

            if isbn:
                book.isbn = isbn

            if section_name:
                section = SectionModel.query.filter_by(name=section_name).first()
                if not section:
                    return {"message": "Section does not exist"}, 400
                book.section_id = section.id

            if name:
                book.name = name

            if authors:
                author_names_list: List[str] = [
                    author_name.strip() for author_name in authors.split(",")
                ]
                BookAuthorModel.query.filter_by(book_id=book_id).delete()

                for author in author_names_list:
                    author_search_word = raw(author)
                    book_author = BookAuthorModel(book_id=book_id, author_name=author, search_word=author_search_word)  # type: ignore
                    db.session.add(book_author)

            if page_count:
                book.page_count = page_count

            if content_path:
                old_content = book.content
                try:
                    old_path = os.path.join(upload_folder, old_content[6:])
                    old_path = old_path.replace("\\", "/")
                    os.remove(old_path)
                except Exception as e:
                    return str(e)
                book.content = "books/" + filename
                book_file.save(content_path)

            if publisher:
                book.publisher = publisher

            if volume:
                book.volume = volume

            if price:
                book.price = price

            section = SectionModel.query.filter_by(id=book.section_id).first()
            if not section:
                return {"message": "Section does not exist"}, 500

            book.search_word = (
                raw(book.isbn)
                + raw(book.name)
                + raw(book.publisher)
                + raw(section.name)
                + raw(str(book.volume))
                + raw(str(book.page_count))
            )

            db.session.commit()

            return {"message": "Book info changed successfully"}, 201

        except Exception as e:
            return {"error": str(e)}, 500


class EditSection(Resource):
    @login_required
    @check_role(role="Librarian")
    def put(self):
        args = reqParser.parse_args()
        try:
            id = args["section_id"]
            if not id:
                return {"message": "Section id not given"}, 400

            section = SectionModel.query.filter_by(id=id).first()
            if not section:
                return {"message": "Section not found"}, 404

            name = args["section_name"]
            description = args["description"]

            this_section = SectionModel.query.filter_by(id=id).first()
            if not this_section:
                return {"message": "Section not found"}, 404

            section = SectionModel.query.filter_by(name=name).first()
            if section and not section.id == this_section.id:
                return {"message": "Section name already exists"}, 404

            if name:
                this_section.name = name

            if description:
                this_section.description = description

            this_section.search_word = raw(this_section.name) + raw(
                this_section.description
            )

            db.session.commit()

            return {"message": "Section Edited Successfully"}, 201

        except Exception as e:
            return {"error": str(e)}


class RevokeBookAccess(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            username = args["username"]
            isbn = args["isbn"]

            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            user_login = UserLoginModel.query.filter_by(username=username).first()
            if not user_login:
                return {"message": "User login does not exist"}, 404

            book_issue = BookIssueModel.query.filter_by(
                uid=user_login.id, book_id=book.id
            ).first()
            if not book_issue:
                return {"message": "Book Issue does not exist"}, 404

            BookIssueModel.query.filter_by(uid=user_login.id, book_id=book.id).delete()
            db.session.commit()

            return {
                "message": f"Revoked access of user {username} from book with isbn {isbn}"
            }, 200

        except Exception as e:
            return {"error": str(e)}, 500


class RemoveSection(Resource):
    @login_required
    @check_role(role="Librarian")
    def delete(self):
        args = reqParser.parse_args()
        try:
            name = args["section_name"]

            if not name:
                return {"message": "Section name not given"}, 400

            section = SectionModel.query.filter_by(name=name).first()
            if not section:
                return {"message": f"Section {name} does not exist"}, 404

            BookModel.query.filter_by(section_id=section.id).update({"section_id": 0})
            SectionModel.query.filter_by(name=name).delete()
            db.session.commit()

            return {"message": f"Section {name} deleted successfully"}, 200

        except Exception as e:
            return {"error": str(e)}, 500


class RemoveBook(Resource):
    @login_required
    @check_role(role="Librarian")
    def delete(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            book = BookModel.query.filter_by(isbn=isbn).first()
            if not book:
                return {"message": f"Book with isbn {isbn} does not exist"}

            old_content = book.content
            try:
                old_path = os.path.join(upload_folder, old_content[6:])
                os.remove(old_path)
            except Exception as e:
                return str(e)

            BookAuthorModel.query.filter_by(book_id=book.id).delete()
            BookModel.query.filter_by(isbn=isbn).delete()
            BookRequestsModel.query.filter_by(book_id=book.id).delete()
            BookIssueModel.query.filter_by(book_id=book.id).delete()
            BookFeedbackModel.query.filter_by(book_id=book.id).delete()
            db.session.commit()

            return {"message": f"Book {book.name} deleted successfully"}

        except Exception as e:
            return {"error": str(e)}, 500


class SearchBook(Resource):
    @login_required
    def get(self):
        try:
            search_word = request.args.get("search_word", default="")
            modified_search_word = "%" + raw(search_word) + "%"

            all_hits = []

            book_hits = (
                BookModel.query.filter(BookModel.search_word.like(modified_search_word))
                .join(SectionModel, onclause=SectionModel.id == BookModel.section_id)
                .with_entities(
                    BookModel.id,
                    BookModel.isbn,
                    BookModel.name,
                    BookModel.content,
                    BookModel.page_count,
                    BookModel.publisher,
                    BookModel.volume,
                    BookModel.section_id,
                    BookModel.search_word,
                    SectionModel.name.label("section_name"),
                    BookModel.price,
                )
                .all()
            )

            author_hits = (
                BookAuthorModel.query.filter(
                    BookAuthorModel.search_word.like(modified_search_word)
                )
                .join(BookModel, onclause=BookAuthorModel.book_id == BookModel.id)
                .join(SectionModel, onclause=SectionModel.id == BookModel.section_id)
                .with_entities(
                    BookModel.id,
                    BookModel.isbn,
                    BookModel.name,
                    BookModel.content,
                    BookModel.page_count,
                    BookModel.publisher,
                    BookModel.volume,
                    BookModel.section_id,
                    BookModel.search_word,
                    SectionModel.name.label("section_name"),
                    BookModel.price,
                )
                .all()
            )

            section_hits = (
                SectionModel.query.filter(
                    SectionModel.search_word.like(modified_search_word)
                )
                .join(BookModel, onclause=SectionModel.id == BookModel.section_id)
                .with_entities(
                    BookModel.id,
                    BookModel.isbn,
                    BookModel.name,
                    BookModel.content,
                    BookModel.page_count,
                    BookModel.publisher,
                    BookModel.volume,
                    BookModel.section_id,
                    BookModel.search_word,
                    SectionModel.name.label("section_name"),
                    BookModel.price,
                )
                .all()
            )

            if book_hits:
                for book in book_hits:
                    # For unique books
                    if book.id in [book_hit.id for book_hit in all_hits]:
                        continue
                    all_hits.append(book)

            if author_hits:
                for book in author_hits:
                    if book.id in [book_hit.id for book_hit in all_hits]:
                        continue
                    all_hits.append(book)

            if section_hits:
                for book in section_hits:
                    if book.id in [book_hit.id for book_hit in all_hits]:
                        continue
                    all_hits.append(book)

            if len(all_hits) == 0:
                return {"message": "No book found"}, 404

            outputList = []
            for book in all_hits:
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section does not exist"}, 404
                outputList.append(
                    {
                        "id": book.id,
                        "isbn": book.isbn,
                        "name": book.name,
                        "page_count": book.page_count,
                        "content": book.content,
                        "publisher": book.publisher,
                        "section_id": book.section_id,
                        "section_name": section.name,
                        "price": book.price,
                    }
                )
            return outputList

        except Exception as e:
            return {"error": str(e)}, 500


class SearchSection(Resource):
    @login_required
    def get(self):
        try:
            search_word = request.args.get("search_word", default="")

            modified_search_word = "%" + raw(search_word) + "%"

            sections = SectionModel.query.filter(
                SectionModel.search_word.like(modified_search_word)
            ).all()

            user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
            if not user_info:
                return {"message": "User info not found"}, 404

            return [
                {
                    "id": section.id,
                    "name": section.name,
                    "description": section.description,
                    "date_created": str(section.date_created),
                }
                for section in sections
            ]

        except Exception as e:
            return {"error": str(e)}, 500


api.add_resource(AddUser, "/api/addUser")
api.add_resource(Login, "/api/login")
api.add_resource(UserInfo, "/api/userInfo")
api.add_resource(Logout, "/api/logout")
api.add_resource(AddSection, "/api/addSection")
api.add_resource(AddBook, "/api/addBook")
api.add_resource(ViewSections, "/api/viewSections")
api.add_resource(ViewBooks, "/api/viewBooks")
api.add_resource(RequestBook, "/api/requestBook")
api.add_resource(ViewBookRequests, "/api/viewBookRequests")
api.add_resource(IssueBook, "/api/issueBook")
api.add_resource(ViewIssuedBooks, "/api/viewIssuedBooks")
api.add_resource(ReturnBook, "/api/returnBook")
api.add_resource(BookFeedback, "/api/bookFeedback")
api.add_resource(ViewFeedbacks, "/api/viewFeedbacks")
api.add_resource(EditBook, "/api/editBook")
api.add_resource(EditSection, "/api/editSection")
api.add_resource(RevokeBookAccess, "/api/revokeBookAccess")
api.add_resource(RemoveSection, "/api/removeSection")
api.add_resource(RemoveBook, "/api/removeBook")
api.add_resource(SearchBook, "/api/searchBook")
api.add_resource(SearchSection, "/api/searchSection")
