from flask import Flask, redirect, render_template, request, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from sqlalchemy.orm import aliased
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
import os
from blueprints.api import UserInfo, api_bp, check_role, login_manager, check_role
from datetime import datetime, timedelta
from typing import List

currentDirectory = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{os.path.join(currentDirectory, "db.sqlite3")}'
app.config["SECRET_KEY"] = "PsIK>@%=`TiDs$>"

db.init_app(app)

app.app_context().push()

login_manager.init_app(app)
app.register_blueprint(api_bp)

login_manager = LoginManager()


@login_manager.user_loader
def load_user(id):
    return UserLoginModel.query.get(id)


@app.route("/", methods=["GET"])
def home():
    return redirect("/librarianLogin")
    # return render_template("home.html")


@app.route("/librarianLogin", methods=["GET", "POST"])
def librarianLogin():
    if request.method == "GET":
        return render_template("login.html", role="librarian")

    username = request.form.get("username")
    password = request.form.get("password")
    role = "Librarian"

    userLogin = UserLoginModel.query.filter_by(username=username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/librarianLogin")

    userInfo = UserInfoModel.query.filter_by(username=username).first()
    if userLogin and not userInfo:
        flash(f"There is no info regarding user {username}")
        return redirect("/librarianLogin")

    if userLogin and userLogin.password == password:
        if userInfo and userInfo.role != role:
            flash(f"{username} is not a {role}")
            return redirect("/librarianLogin")
        else:
            login_user(userLogin)
    else:
        flash(f"Incorrect Password")
        return redirect("/librarianLogin")

    return redirect("/librarianDashboard/sections")


@app.route("/generalLogin", methods=["GET", "POST"])
def generalLogin():
    if request.method == "GET":
        return render_template("login.html", role="general")

    username = request.form.get("username")
    password = request.form.get("password")
    role = "General"

    userLogin = UserLoginModel.query.filter_by(username=username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/generalLogin")

    userInfo = UserInfoModel.query.filter_by(username=username).first()
    if userLogin and not userInfo:
        flash(f"There is no info regarding user {username}")
        return redirect("/generalLogin")

    if userLogin and userLogin.password == password:
        if userInfo and userInfo.role != role:
            flash(f"{username} is not a {role}")
            return redirect("/generalLogin")
        else:
            login_user(userLogin)
    else:
        flash(f"Incorrect Password")
        return redirect("/generalLogin")

    return redirect("/generalDashboard")


@app.route("/logout", methods=["GET"])
def logout():
    logout_user()
    return redirect("/")


@app.route("/addUser", methods=["GET", "POST"])
def addUser():
    if request.method == "GET":
        return render_template("addUser.html")

    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    role = "General"

    userLogin = UserLoginModel(username=username, password=password)  # type: ignore
    userInfo = UserInfoModel(username=username, first_name=first_name, last_name=last_name, role=role)  # type: ignore
    db.session.add(userLogin)
    db.session.add(userInfo)
    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/librarianDashboard/sections", methods=["GET"])
@login_required
@check_role(role="Librarian")
def sections():
    sections = SectionModel.query.all()
    return render_template("sections.html", sections=sections)


@app.route("/addSection", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addSection():
    if request.method == "GET":
        return render_template("addSection.html")

    name = request.form.get("name")
    description = request.form.get("description")
    section = SectionModel(name=name.capitalize(), description=description, date_created=datetime.now())  # type: ignore

    db.session.add(section)
    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/<section_name_from_url>/addBook", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addBook(section_name_from_url: str):
    if request.method == "GET":
        return render_template("addBook.html", section=section_name_from_url)

    isbn = request.form.get("isbn")
    book_name = request.form.get("book_name")
    page_count = request.form.get("page_count")
    content_path = request.form.get("content")
    publisher = request.form.get("publisher")
    section_name = section_name_from_url.capitalize()
    author_names = request.form.get("author_names")

    section = SectionModel.query.filter_by(name=section_name).first()

    if not section:
        return {"message": "Section does not exist"}, 404

    if not author_names:
        return {"message": "Author names not given"}, 404

    author_names_list: List[str] = author_names.split(",")

    book = BookModel.query.filter_by(isbn=isbn).first()

    if book:
        return {"message": "Book already exists"}, 400

    book = BookModel(isbn=isbn, name=book_name, page_count=page_count, content=content_path, publisher=publisher, section_id=section.id)  # type: ignore
    db.session.add(book)

    for author_name in author_names_list:
        author = BookAuthorModel(isbn=isbn, author_name=author_name)  # type: ignore
        db.session.add(author)
    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/<section_name_from_url>/viewBooks", methods=["GET"])
@login_required
def viewBooks(section_name_from_url):

    section_name = section_name_from_url.capitalize()
    section = SectionModel.query.filter_by(name=section_name).first()

    if not section:
        return {"message": "Section not found"}

    books = BookModel.query.filter_by(section_id=section.id)

    return render_template("viewBooks.html", books=books)


@app.route("/generalDashboard", methods=["GET"])
@login_required
def generalDashboard():
    info = UserInfoModel.query.filter_by(username=current_user.username).first()
    if not info:
        return {"message": "User info does not exist"}
    return render_template("dashboardStats.html", role=info.role)


@app.route("/generalDashboard/requestBooks", methods=["GET"])
@login_required
def requestBooks():
    
    query = db.session.query(BookModel, SectionModel).join(SectionModel, onclause=SectionModel.id == BookModel.section_id).all()

    return render_template("allBooks.html", books = query)

@app.route("/requestBook/<isbn>", methods = ["GET", "POST"])
@login_required
def requestBook(isbn: str):
    if request.method == "GET": 
        return render_template("requestForm.html", isbn = isbn)
    
    issue_time = request.form.get("issue_time")
    
    book_request = BookRequestsModel.query.filter_by(isbn = isbn, username = current_user.username).first()
    if book_request:
        return {"message": "Book request already exists"}

    book_issue = BookIssueModel.query.filter_by(isbn = isbn, username = current_user.username).first()
    if book_issue:
        return {"message": "Book has already been issued"}

    book_request = BookRequestsModel(isbn = isbn, username = current_user.username, date_of_request=datetime.now(), issue_time=issue_time)  # type: ignore
    db.session.add(book_request)
    db.session.commit()

    return redirect("/generalDashboard/requestBooks")

@app.route("/generalDashboard/books", methods = ["GET", "POST"])
@login_required
def generalBooks():
    if request.method == "GET":

        requested = db.session.query(BookRequestsModel, BookModel).join(BookRequestsModel, onclause=BookRequestsModel.isbn == BookModel.isbn).filter_by(username = current_user.username).all()
        issued = db.session.query(BookIssueModel, BookModel).join(BookIssueModel, onclause=BookIssueModel.isbn == BookModel.isbn).filter_by(username = current_user.username).all()

        return render_template("generalBooks.html", issued = issued, requested = requested)
    
    return ""


if __name__ == "__main__":
    app.run(debug=True)
