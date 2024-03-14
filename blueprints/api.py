from flask import Blueprint, request
from flask_restful import Resource, reqparse, Api
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
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
from datetime import datetime, timedelta

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

reqParser.add_argument("feedback", type=str)
reqParser.add_argument("old_to_new_author", type=str)
reqParser.add_argument("new_isbn", type=str)


# Decorator function to verify role
def check_role(role: str):
    def decorator(function: Callable):
        def wrapper(*args, **kwargs):
            info = UserInfoModel.query.filter_by(username=current_user.username).first()

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
            return {"error": f"{e}"}, 500


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
                    return {"message": f"{role} user Login successful. Welcome {info.first_name}"}, 200
                else:
                    # Password does not match
                    return {"message": "Incorrect password"}, 400
            else:
                # User does not exist
                return {"message": f"{role} user does not exist"}, 404

        except Exception as e:
            return {"error": f"{e}"}, 500


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

        return {
            "username": userLogin.username,
            "password": userLogin.password,
            "first_name": info.first_name,
            "last_name": last_name,
            "role": info.role,
        }, 200


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

            date_created = datetime.now()

            section = SectionModel(name=name, date_created=date_created, description=description)  # type: ignore
            db.session.add(section)
            db.session.commit()

            return {"message": f"Section {name} added successfully"}, 201

        except Exception as e:
            return {"error": f"{e}"}, 500


class AddBookAuthor(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        try:
            args = reqParser.parse_args()
            isbn = args["isbn"]
            book_name = args["book_name"]
            page_count = args["page_count"]
            section_name = args["section_name"]
            content_path = args["content"]
            publisher = args["publisher"]
            author_names: str = args["author_names"]
            author_names_list: List[str] = author_names.split(",")

            section = SectionModel.query.filter_by(name=section_name).first()

            if not section:
                return {"message": "Section does not exist"}, 404

            book = BookModel.query.filter_by(isbn=isbn).first()

            if book:
                return {"message": "Book already exists"}, 400

            book = BookModel(isbn=isbn, name=book_name, page_count=page_count, content=content_path, publisher=publisher, section_id=section.id)  # type: ignore
            db.session.add(book)
            db.session.commit()

            for author_name in author_names_list:
                book_author = BookAuthorModel(book_id=book.id, author_name=author_name)  # type: ignore
                db.session.add(book_author)
            db.session.commit()

            return {"message": f"Book {book_name} with authors {author_names} added successfully"}, 201

        except Exception as e:
            return {"error": f"{e}"}, 500


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
                    "date_created": str(section.date_created),
                    "description": section.description,
                }
                for section in sections
            ], 200

        except Exception as e:
            return {"error": f"{e}"}, 500


class ViewAllBooks(Resource):
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
                    }
                )

            return outputList

        except Exception as e:
            return {"error": f"{e}"}, 500


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
            
            book_request = BookRequestsModel.query.filter_by(book_id=book.id, username=current_user.username).first()
            if book_request:
                return {"message": "Book already requested"}, 400

            book_issue = BookIssueModel.query.filter_by(book_id=book.id, username=current_user.username).first()
            if book_issue:
                return {"message": "Book has already been issued"}, 400


            book_request = BookRequestsModel(book_id = book.id, username=current_user.username, date_of_request=datetime.now(), issue_time=issue_time)  # type: ignore
            db.session.add(book_request)
            db.session.commit()

            return {"message": f"Book {book.name} requested successfully"}, 201

        except Exception as e:
            return {"error": f"{e}"}, 500


class ViewBookRequests(Resource):
    @login_required
    @check_role(role="Librarian")
    def get(self):
        try:
            book_requests = BookRequestsModel.query.all()
            return [
                {"book_id": book_request.book_id, "username": book_request.username, "issue_time": book_request.issue_time}
                for book_request in book_requests
            ]

        except Exception as e:
            return {"error": f"{e}"}, 500


class IssueBook(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            username = args["username"]

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_request = BookRequestsModel.query.filter_by(book_id = book.id, username=username).first()

            if not book_request:
                return {"message": "Book request does not exist"}, 404

            book_issue = BookIssueModel(book_id=book.id, username=username, date_of_issue=datetime.now(), date_of_return=datetime.now() + timedelta(days=book_request.issue_time))  # type: ignore
            db.session.add(book_issue)

            BookRequestsModel.query.filter_by(book_id=book.id, username=username).delete()
            db.session.commit()

            return {"message": f"Book {book.name} issued to {username} successfully"}, 201

        except Exception as e:
            return {"error": f"{e}"}, 500


class ViewIssuedBooks(Resource):
    @login_required
    def get(self):
        info = UserInfoModel.query.filter_by(username=current_user.username).first()
        if not info:
            return {"message": "User info does not exist"}, 404

        try:
            if info.role == "General":
                username = current_user.username
            else:
                username = request.args.get("username", default="testUname")

            book_issue = BookIssueModel.query.filter_by(username=username).all()

            outputList = []
            for issued_book in book_issue:
                book = BookModel.query.filter_by(isbn=issued_book.isbn).first()
                if not book:
                    return {"message": "Book does not exist"}, 404
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section does not exist"}, 404
                outputList.append(
                    {
                        "isbn": book.isbn,
                        "name": book.name,
                        "page_count": book.page_count,
                        "content": book.content,
                        "publisher": book.publisher,
                        "section_id": book.section_id,
                        "section_name": section.name,
                    }
                )

            return outputList

        except Exception as e:
            return {"error": f"{e}"}


class ReturnBook(Resource):
    @login_required
    @check_role(role="General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            username = current_user.username

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_issue = BookIssueModel.query.filter_by(book_id=book.id, username=username).first()

            if not book_issue:
                return {"message": f"Book with isbn {isbn} is not issued by user {username}"}, 404

            BookIssueModel.query.filter_by(book_id=book.id, username=username).delete()
            db.session.commit()

            return {"message": f"Book {book.name} has been returned"}, 200

        except Exception as e:
            return {"error": f"{e}"}, 500


class BookFeedback(Resource):
    @login_required
    @check_role(role="General")
    def post(self):
        args = reqParser.parse_args()
        try:
            isbn = args["isbn"]
            feedback = args["feedback"]

            username = current_user.username

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_feedback = BookFeedbackModel(book_id=book.id, username=username, feedback=feedback)  # type: ignore
            db.session.add(book_feedback)
            db.session.commit()

            return {"message": f"Feedback for {book.name} submitted successfully"}, 200

        except Exception as e:
            return {"error": f"{e}"}, 500


class ViewFeedbacks(Resource):
    @login_required
    @check_role(role="Librarian")
    def get(self):
        try:
            isbn = request.args.get("isbn", default=None)

            book = BookModel.query.filter_by(isbn = isbn).first()
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
                {"isbn": isbn, "username": feedback.username, "feedback": feedback.feedback}
                for feedback in feedbacks
            ]

        except Exception as e:
            return {"error": f"{e}"}, 500


class EditBookInfo(Resource):
    @login_required
    @check_role(role="Librarian")
    def put(self):
        args = reqParser.parse_args()
        try:
            book_id = args["book_id"]
            new_isbn = args["new_isbn"]
            name = args["book_name"]
            old_to_new_author = args["old_to_new_author"]
            page_count = args["page_count"]
            content_path = args["content"]
            publisher = args["publisher"]
            section_name = args["section_name"]

            oldAuthor, newAuthor = None, None
            if old_to_new_author:
                oldAuthor, newAuthor = tuple(old_to_new_author.split(","))

            book = BookModel.query.filter_by(id = book_id).first()
            if not book:
                return {"message": f"Book does not exist"}, 404

            if oldAuthor:
                book_author = BookAuthorModel.query.filter_by(book_id = book_id, author_name=oldAuthor).first()
                if not book_author:
                    return {"message": f"ISBN does not exist or Author {oldAuthor} does not exist"}, 404

            section = SectionModel.query.filter_by(name=section_name).first()

            if new_isbn:
                book.isbn = new_isbn

            if name:
                book.name = name

            if page_count:
                book.page_count = page_count

            if section:
                book.section_id = section.id

            if content_path:
                book.content = content_path

            if publisher:
                book.publisher = publisher

            book_author = None
            if book_author:
                if new_isbn:
                    book_author.isbn = new_isbn
                book_author.author_name = newAuthor

            db.session.commit()

            return {"message": "Book info changed successfully"}

        except Exception as e:
            return {"error": f"{e}"}, 500


class RevokeBookAccess(Resource):
    @login_required
    @check_role(role="Librarian")
    def post(self):
        args = reqParser.parse_args()
        try:
            username = args["username"]
            isbn = args["isbn"]

            book = BookModel.query.filter_by(isbn = isbn).first()
            if not book:
                return {"message": "Book does not exist"}, 404

            book_issue = BookIssueModel.query.filter_by(username=username, book_id=book.id).first()
            if not book_issue:
                return {"message": "Book Issue does not exist"}, 404

            BookIssueModel.query.filter_by(username=username, book_id=book.id).delete()
            db.session.commit()

            return {"message": f"Revoked access of user {username} from book with isbn {isbn}"}

        except Exception as e:
            return {"error": f"{e}"}, 500


class RemoveSection(Resource):
    @login_required
    @check_role(role="Librarian")
    def delete(self):
        args = reqParser.parse_args()
        try:
            name = args["section_name"]
            section = SectionModel.query.filter_by(name=name).first()
            if not section:
                return {"message": f"Section {name} does not exist"}, 404

            BookModel.query.filter_by(section_id=section.id).update({"section_id": -1})
            SectionModel.query.filter_by(name=name).delete()
            db.session.commit()

            return {"message": f"Section {name} deleted successfully"}, 200

        except Exception as e:
            return {"error": f"{e}"}, 500


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

            BookAuthorModel.query.filter_by(book_id=book.id).delete()
            BookModel.query.filter_by(isbn=isbn).delete()
            db.session.commit()

            return {"message": f"Book {book.name} deleted successfully"}

        except Exception as e:
            return {"error": f"{e}"}, 500


class FindBook(Resource):
    @login_required
    def get(self):
        try:
            isbn = request.args.get("isbn", default=None)
            book_name = request.args.get("name", default=None)
            author_name = request.args.get("author_name", default=None)
            publisher = request.args.get("publisher", default=None)

            books = None
            if isbn:
                books = BookModel.query.filter_by(isbn=isbn).all()
            elif book_name:
                books = BookModel.query.filter_by(name=book_name).all()
            elif publisher:
                books = BookModel.query.filter_by(publisher=publisher).all()
            elif author_name:
                books = (
                    BookModel.query.join(BookAuthorModel, BookAuthorModel.book_id == BookModel.id)
                    .filter_by(author_name=author_name)
                    .with_entities(
                        BookModel.isbn, BookModel.name, BookModel.page_count, BookModel.content, BookModel.section_id
                    )
                    .all()
                )

            if not books:
                return {"message": "No book found"}, 404

            outputList = []
            for book in books:
                section = SectionModel.query.filter_by(id=book.section_id).first()
                if not section:
                    return {"message": "Section does not exist"}, 404
                outputList.append(
                    {
                        "isbn": book.isbn,
                        "name": book.name,
                        "page_count": book.page_count,
                        "content": book.content,
                        "publisher": book.publisher,
                        "section_id": book.section_id,
                        "section_name": section.name,
                    }
                )
            return outputList

        except Exception as e:
            return {"error": f"{e}"}, 500


class FindSection(Resource):
    @login_required
    def get(self):
        try:
            id = request.args.get("section_id")
            name = request.args.get("section_name")

            section = None
            if id:
                section = SectionModel.query.filter_by(id=id).first()

            elif name:
                section = SectionModel.query.filter_by(name=name).first()

            if not section:
                return {"message": "No section found"}, 404

            return {
                "id": section.id,
                "name": section.name,
                "date_created": str(section.date_created),
                "description": section.description,
            }

        except Exception as e:
            return {"error": f"{e}"}, 500


api.add_resource(AddUser, "/api/addUser")
api.add_resource(Login, "/api/login")
api.add_resource(UserInfo, "/api/userInfo")
api.add_resource(Logout, "/api/logout")
api.add_resource(AddSection, "/api/addSection")
api.add_resource(AddBookAuthor, "/api/addBookAuthor")
api.add_resource(ViewSections, "/api/viewSections")
api.add_resource(ViewAllBooks, "/api/viewAllBooks")
api.add_resource(RequestBook, "/api/requestBook")
api.add_resource(ViewBookRequests, "/api/viewBookRequests")
api.add_resource(IssueBook, "/api/issueBook")
api.add_resource(ViewIssuedBooks, "/api/viewIssuedBooks")
api.add_resource(ReturnBook, "/api/returnBook")
api.add_resource(BookFeedback, "/api/bookFeedback")
api.add_resource(ViewFeedbacks, "/api/viewFeedbacks")
api.add_resource(EditBookInfo, "/api/editBookInfo")
api.add_resource(RevokeBookAccess, "/api/revokeBookAccess")
api.add_resource(RemoveSection, "/api/removeSection")
api.add_resource(RemoveBook, "/api/removeBook")
api.add_resource(FindBook, "/api/findBook")
api.add_resource(FindSection, "/api/findSection")
