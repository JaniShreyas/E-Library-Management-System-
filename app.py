from tabnanny import check
from flask import Flask, redirect, render_template, request, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from numpy import delete
from sqlalchemy import desc
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
    user_info = UserInfoModel.query.filter_by(username = current_user.username).first()
    if not user_info:
        return {"message": "User info does not exist"}
    role = user_info.role
    return render_template("sections.html", sections=sections, role=role)


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


# Don't restrict by role since used by both users
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

        book_request = BookRequestsModel.query.filter_by(username = current_user.username).all()
        book_issue = BookIssueModel.query.filter_by(username = current_user.username).all()
        if (len(book_request) + len(book_issue)) >= 5:
            return {"message": "You can only request/issue 5 books at once"}

        return render_template("requestForm.html", isbn = isbn)
    
    issue_time = int(request.form.get("issue_time", 8))

    if not (1 < issue_time < 8):
        return {"message": "Issue time should be in range (1,7)"}
    
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

@app.route("/librarianDashboard/viewRequests", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def viewRequests():
    book_requests = BookRequestsModel.query.all()
    return render_template("viewRequests.html", requests = book_requests)

@app.route("/viewRequests/dealWithRequest", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def dealWithRequest():
    isbn = request.args.get("isbn")
    username = request.args.get("username")
    issue_time = request.args.get("issue_time")
    accept = request.args.get("accept")

    if accept not in ('0','1'):
        return {"message": "accept should be in (0,1)"}, 400
    
    if accept == '1':
        # Accept book

        book_issue = BookIssueModel.query.filter_by(isbn = isbn, username = username).first()
        if book_issue:
            return {"message": "Book Issue already exists"}, 400

        book = BookModel.query.filter_by(isbn = isbn).first()
        if not book: 
            return {"message": "Book does not exist"}, 400

        book_issue = BookIssueModel(isbn = isbn, username = username, date_of_issue = datetime.now(), date_of_return = datetime.now() + timedelta(int(issue_time)))  # type: ignore

        BookRequestsModel.query.filter_by(isbn = isbn, username = username).delete()

        db.session.add(book_issue)
        db.session.commit()

        return redirect("/librarianDashboard/viewRequests")

    else:
        # Reject book
        BookRequestsModel.query.filter_by(isbn = isbn, username = username).delete()
        db.session.commit()
        return redirect("/librarianDashboard/viewRequests")

@app.route("/returnBook", methods=["GET"])
@login_required
def returnBook():
    isbn = request.args.get("isbn")
    book_issue = BookIssueModel.query.filter_by(username = current_user.username, isbn = isbn)
    if not book_issue:
        return {"message": "Book issue does not exist"}
    
    BookIssueModel.query.filter_by(username = current_user.username, isbn = isbn).delete()
    db.session.commit()

    return redirect(f"/feedback?isbn={isbn}")

@app.route("/feedback", methods = ["GET", "POST"])
@login_required
def feedback():
    if request.method == "GET":
        isbn = request.args.get("isbn")
        return render_template("feedback.html", isbn = isbn)        

    isbn = request.form.get("isbn")
    feedback = request.form.get("feedback")

    book_feedback = BookFeedbackModel(username = current_user.username, isbn = isbn, feedback = feedback)  # type: ignore
    db.session.add(book_feedback)
    db.session.commit()

    return redirect("/generalDashboard/books")

@app.route("/generalDashboard/sections", methods = ["GET"])
@login_required
def generalViewSections():
    sections = SectionModel.query.all()
    user_info = UserInfoModel.query.filter_by(username = current_user.username).first()
    if not user_info:
        return {"message": "User info does not exist"}
    role = user_info.role
    return render_template("sections.html", sections=sections, role = role)

@app.route("/librarianDashboard/revokeAccess", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def librarianDashboarRevokeAccess():
    
    book_issues = BookIssueModel.query.all()
    return render_template("revokeAccess.html", book_issues = book_issues)

@app.route("/revokeAccess", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def revokeAccess():
    isbn = request.args.get("isbn")
    username = request.args.get("username")

    book_issue = BookIssueModel.query.filter_by(isbn = isbn, username = username).first()
    if not book_issue:
        return {"message": "Book issue does not exist"}
    
    BookIssueModel.query.filter_by(isbn = isbn, username = username).delete()
    db.session.commit()

    return redirect("/librarianDashboard/revokeAccess")

@app.route("/editSection", methods = ["GET", "POST"])
@login_required
@check_role(role = "Librarian")
def editSection():
    id = request.args.get("id")
    if request.method == "GET":
        return render_template("editSection.html", id = id)
    
    id = request.form.get("id")
    name = request.form.get("name")
    description = request.form.get("description")

    section = SectionModel.query.filter_by(id = id).first()
    
    if not section:
        return {"message": "Section not found"}

    if name:
        section.name = name
    
    if description:
        section.description = description

    db.session.commit()
    return redirect("/librarianDashboard/sections")

if __name__ == "__main__":
    app.run(debug=True)
