from gettext import find
from re import search
from flask import Flask, redirect, render_template, request, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from sqlalchemy import desc
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
from blueprints.api import api_bp, check_role, login_manager, check_role
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

max_issue_time = 7

def raw(input: str) -> str:
    return input.lower().replace(' ', "")

def findBooks(search_word: str, filter_section = None):
    modified_search_word = '%'+raw(search_word)+'%'
    all_hits = []

    if filter_section:
        book_hits = BookModel.query.filter(BookModel.search_word.like(modified_search_word)).filter_by(section_id = filter_section).all()

        author_hits = BookAuthorModel.query.filter(BookAuthorModel.search_word.like(modified_search_word))\
            .join(BookModel, onclause=BookAuthorModel.book_id == BookModel.id)\
            .filter_by(section_id = filter_section)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookModel.content, 
                            BookModel.page_count, BookModel.publisher, BookModel.volume, 
                            BookModel.section_id, BookModel.search_word).all()
        
        section_hits = SectionModel.query.filter(SectionModel.search_word.like(modified_search_word))\
            .join(BookModel, onclause=SectionModel.id == BookModel.section_id)\
            .filter_by(section_id = filter_section)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookModel.content, 
                        BookModel.page_count, BookModel.publisher, BookModel.volume, 
                        BookModel.section_id, BookModel.search_word).all()
        
    else:
        book_hits = BookModel.query.filter(BookModel.search_word.like(modified_search_word))\
            .join(SectionModel, onclause=SectionModel.id == BookModel.section_id)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookModel.content, 
                            BookModel.page_count, BookModel.publisher, BookModel.volume, 
                            BookModel.section_id, BookModel.search_word, SectionModel.name.label("section_name")).all()

        author_hits = BookAuthorModel.query.filter(BookAuthorModel.search_word.like(modified_search_word))\
            .join(BookModel, onclause=BookAuthorModel.book_id == BookModel.id)\
            .join(SectionModel, onclause=SectionModel.id == BookModel.section_id)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookModel.content, 
                            BookModel.page_count, BookModel.publisher, BookModel.volume, 
                            BookModel.section_id, BookModel.search_word, SectionModel.name.label("section_name")).all()
        
        section_hits = SectionModel.query.filter(SectionModel.search_word.like(modified_search_word))\
            .join(BookModel, onclause=SectionModel.id == BookModel.section_id)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookModel.content, 
                           BookModel.page_count, BookModel.publisher, BookModel.volume, 
                           BookModel.section_id, BookModel.search_word, SectionModel.name.label("section_name")).all()
    
    if book_hits:
        for book in book_hits:
            # For unique books
            if book.id in [book_hit.id for book_hit in all_hits]: continue
            all_hits.append(book)

    if author_hits:
        for book in author_hits:
            if book.id in [book_hit.id for book_hit in all_hits]: continue
            all_hits.append(book)

    if section_hits:
        for book in section_hits:
            if book.id in [book_hit.id for book_hit in all_hits]: continue
            all_hits.append(book)

    return all_hits

def get_all_book_authors():
    return BookAuthorModel.query.all()

@login_manager.user_loader
def load_user(id):
    return UserLoginModel.query.get(id)


@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/librarianLogin/", methods=["GET", "POST"])
def librarianLogin():
    if request.method == "GET":
        if current_user:
            return redirect("/librarianDashboard")

        return render_template("login.html", role="librarian")

    username = request.form.get("username")
    password = request.form.get("password")
    role = "Librarian"

    userLogin = UserLoginModel.query.filter_by(username=username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/librarianLogin")

    userInfo = UserInfoModel.query.filter_by(uid=userLogin.id).first()
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

    return redirect("/librarianDashboard")


@app.route("/generalLogin/", methods=["GET", "POST"])
def generalLogin():
    if request.method == "GET":
        if current_user:
            return redirect("/generalDashboard")
        return render_template("login.html", role="general")

    username = request.form.get("username")
    password = request.form.get("password")
    role = "General"

    userLogin = UserLoginModel.query.filter_by(username=username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/generalLogin")

    userInfo = UserInfoModel.query.filter_by(uid=userLogin.id).first()
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

@app.route("/logout/", methods=["GET"])
def logout():
    logout_user()
    return redirect("/")


@app.route("/addUser/", methods=["GET", "POST"])
def addUser():
    if request.method == "GET":
        return render_template("addUser.html")

    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    role = "General"

    user_login = UserLoginModel.query.filter_by(username = username).first()
    if user_login:
        return {"message": "Username already exists"}

    userLogin = UserLoginModel(username=username, password=password)  # type: ignore
    db.session.add(userLogin)
    db.session.commit()
    userInfo = UserInfoModel(uid=userLogin.id, first_name=first_name, last_name=last_name, role=role)  # type: ignore
    db.session.add(userInfo)
    db.session.commit()
    login_user(userLogin)
    return redirect("/generalDashboard")

@app.route("/librarianDashboard/", methods = ["GET"])
def librarianDashboard():
    return render_template("librarianDashboard.html")

@app.route("/librarianDashboard/sections/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def sections():
    sections = SectionModel.query.all()
    user_info = UserInfoModel.query.filter_by(uid = current_user.id).first()
    if not user_info:
        return {"message": "User info does not exist"}
    role = user_info.role
    return render_template("/sections.html", sections=sections, role=role)


@app.route("/addSection/", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addSection():
    if request.method == "GET":
        return render_template("addSection.html")

    name = request.form.get("name")
    if not name:
        return {"message": "Name not provided"}

    description = request.form.get("description")

    search_word = raw(name)
    if description:
        search_word += raw(description)

    section = SectionModel.query.filter_by(name = name).first()
    if section:
        return {"message": f"Section with name {name} already exists"}

    section = SectionModel(name=name, description=description, date_created=datetime.now(), search_word=search_word)  # type: ignore

    db.session.add(section)
    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/addBook/", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addBook():
    if request.method == "GET":
        section_id = request.args.get("section_id")
        if section_id:
            queried_section = SectionModel.query.filter_by(id = section_id).first()
            if not queried_section:
                return {"message": "Section does not exist"}
        sections = SectionModel.query.all()
        return render_template("addBook.html", section_id=section_id, sections = sections)

    section_id = request.args.get("section_id")
    
    isbn = request.form.get("isbn")
    book_name = request.form.get("book_name")
    page_count = request.form.get("page_count")
    content_path = request.form.get("content")
    publisher = request.form.get("publisher")
    volume = request.form.get("volume")
    author_names = request.form.get("author_names")

    try:
        if page_count:
            page_count = int(page_count)
            if page_count < 1:
                return {"message": "Page count must be a positive integer"}
    except ValueError:
        return {"message": "Page count should be an integer"}
    except Exception as e:
        return {"message": str(e)}

    if section_id != 'None':
        section = SectionModel.query.filter_by(id = section_id).first()
    else:
        section_name = request.form.get("section_name")
        section = SectionModel.query.filter_by(name = section_name).first()
        

    if not section:
        return {"message": "Section does not exist"}, 404

    if not author_names:
        return {"message": "Author names not given"}, 404

    author_names_list: List[str] = author_names.split(",")

    if not book_name:
        return {"message": "Book name not provided"}
    if not isbn:
        return {"message": "ISBN not provided"}
    if not publisher:
        return {"message": "Publisher not provided"}

    book = BookModel.query.filter_by(isbn=isbn).first()

    if book:
        return {"message": "Book already exists"}, 400
    
    search_word: str = raw(isbn) + raw(book_name) + raw(publisher) + raw(section.name) + raw(str(volume)) + raw(str(page_count))

    book = BookModel(isbn=isbn, name=book_name, page_count=page_count, content=content_path, 
                     publisher=publisher, volume = volume, section_id=section.id, search_word = search_word)  # type: ignore
    db.session.add(book)
    db.session.commit()

    for author_name in author_names_list:
        author_search_word: str = raw(author_name)
        author = BookAuthorModel(book_id=book.id, author_name=author_name, search_word = author_search_word)  # type: ignore
        db.session.add(author)
    db.session.commit()

    return redirect(f"/viewBooks/{section.id}")


# Don't restrict by role since used by both users
@app.route("/viewBooks/<section_id>", methods=["GET"])
@login_required
def viewBooks(section_id):

    book_authors = get_all_book_authors()

    section = SectionModel.query.filter_by(id = section_id).first()

    if not section:
        return {"message": "Section not found"}

    books = BookModel.query.filter_by(section_id=section.id).all()

    user_info = UserInfoModel.query.filter_by(uid = current_user.id).first()
    if not user_info:
        return {"message": "User info does not exist"}
    
    print(books)

    return render_template("viewBooks.html",section_id = section.id, books=books, role = user_info.role, book_authors = book_authors)

@app.route("/generalDashboard/", methods=["GET"])
@login_required
def generalDashboard():
    return render_template("generalDashboard.html")

@app.route("/generalDashboard/requestBooks/", methods=["GET"])
@login_required
def requestBooks():

    book_authors = get_all_book_authors()

    book_requests = BookRequestsModel.query.filter_by(uid = current_user.id).all()
    book_issues = BookIssueModel.query.filter_by(uid = current_user.id).all()

    issued_book_ids = [book_request.book_id for book_request in book_requests]
    issued_book_ids.extend([book_issue.book_id for book_issue in book_issues])
    print(issued_book_ids)
    books = db.session.query(BookModel, SectionModel).join(SectionModel, onclause=SectionModel.id == BookModel.section_id).all()
    return render_template("allBooks.html", books = books, issued_book_ids = issued_book_ids, book_authors = book_authors)

@app.route("/requestBook/", methods = ["GET", "POST"])
@login_required
def requestBook():

    if request.method == "GET": 
        id = request.args.get("id")

        request_book = BookRequestsModel.query.filter_by(book_id = id, uid = current_user.id).first()
        if request_book: 
            return {"message": "Book request already exists"}
        
        issue_book = BookIssueModel.query.filter_by(book_id = id, uid = current_user.id).first()
        if issue_book:
            return {"message": "Book has already been issued"}

        book_request = BookRequestsModel.query.filter_by(uid = current_user.id).all()
        book_issue = BookIssueModel.query.filter_by(uid = current_user.id).all()
        if (len(book_request) + len(book_issue)) >= 5:
            return {"message": "You can only request/issue 5 books at once"}

        return render_template("requestForm.html", id = id)
    
    id = request.args.get("id")

    try:
        issue_time = int(request.form.get("issue_time", 8))
    except Exception as e:
        return {"message": str(e)}

    if not (1 <= issue_time <= max_issue_time):
        return {"message": "Issue time should be in range (1,7)"}
    
    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}, 404
    
    book_request = BookRequestsModel.query.filter_by(book_id = book.id, uid = current_user.id).first()
    if book_request:
        return {"message": "Book request already exists"}

    book_issue = BookIssueModel.query.filter_by(book_id = book.id, uid = current_user.id).first()
    if book_issue:
        return {"message": "Book has already been issued"}

    book_request = BookRequestsModel(book_id = book.id, uid = current_user.id, date_of_request=datetime.now(), issue_time=issue_time)  # type: ignore
    db.session.add(book_request)
    db.session.commit()

    return redirect("/generalDashboard/requestBooks")

@app.route("/generalDashboard/books/", methods = ["GET", "POST"])
@login_required
def generalBooks():
    if request.method == "GET":

        book_authors = get_all_book_authors()

        requested = db.session.query(BookRequestsModel, BookModel).join(BookRequestsModel, onclause=BookRequestsModel.book_id == BookModel.id).filter_by(uid = current_user.id).all()
        issued = db.session.query(BookIssueModel, BookModel).join(BookIssueModel, onclause=BookIssueModel.book_id == BookModel.id).filter_by(uid = current_user.id).all()

        for issued_book, book in issued:
            if issued_book.date_of_return < datetime.now():
                BookIssueModel.query.filter_by(book_id = issued_book.book_id, uid = current_user.id).delete()

        db.session.commit()
        issued = db.session.query(BookIssueModel, BookModel).join(BookIssueModel, onclause=BookIssueModel.book_id == BookModel.id).filter_by(uid = current_user.id).all()

        return render_template("generalBooks.html", issued = issued, requested = requested, book_authors = book_authors)
    
    return ""

@app.route("/librarianDashboard/viewRequests/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def viewRequests():
    book_requests = BookRequestsModel.query.all()
    return render_template("viewRequests.html", requests = book_requests)

@app.route("/viewRequests/dealWithRequest/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def dealWithRequest():
    id = request.args.get("id")
    uid = request.args.get("uid")
    issue_time = request.args.get("issue_time")
    accept = request.args.get("accept")

    if accept not in ('0','1'):
        return {"message": "accept should be in (0,1)"}, 400
    
    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}, 404
    
    if accept == '1':
        # Accept book

        book_issue = BookIssueModel.query.filter_by(book_id=book.id, uid = uid).first()
        if book_issue:
            return {"message": "Book Issue already exists"}, 400

        book_issue = BookIssueModel(book_id=book.id, uid = uid, date_of_issue = datetime.now(), date_of_return = datetime.now() + timedelta(int(issue_time)))  # type: ignore

        BookRequestsModel.query.filter_by(book_id=book.id, uid = uid).delete()

        db.session.add(book_issue)
        db.session.commit()

        return redirect("/librarianDashboard/viewRequests")

    else:
        # Reject book
        BookRequestsModel.query.filter_by(book_id=book.id, uid = uid).delete()
        db.session.commit()
        return redirect("/librarianDashboard/viewRequests")

@app.route("/returnBook/", methods=["GET"])
@login_required
def returnBook():
    id = request.args.get("id")

    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}, 404

    book_issue = BookIssueModel.query.filter_by(uid = current_user.id, book_id=book.id)
    if not book_issue:
        return {"message": "Book issue does not exist"}
    
    BookIssueModel.query.filter_by(uid = current_user.id, book_id=book.id).delete()
    db.session.commit()

    return redirect(f"/feedback?id={id}")

@app.route("/feedback/", methods = ["GET", "POST"])
@login_required
def feedback():
    if request.method == "GET":
        id = request.args.get("id")
        book = BookModel.query.filter_by(id = id).first()
        if not book:
            return {"message": "Book does not exist"}
        return render_template("feedback.html", book = book)        

    id = request.args.get("id")
    feedback = request.form.get("feedback")

    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}, 404
    
    BookFeedbackModel.query.filter_by(uid = current_user.id, book_id = book.id).delete()

    book_feedback = BookFeedbackModel(uid = current_user.id, book_id=book.id, feedback = feedback)  # type: ignore
    db.session.add(book_feedback)
    db.session.commit()

    return redirect("/generalDashboard/books")

@app.route("/generalDashboard/sections/", methods = ["GET"])
@login_required
def generalViewSections():
    sections = SectionModel.query.all()
    user_info = UserInfoModel.query.filter_by(uid = current_user.id).first()
    if not user_info:
        return {"message": "User info does not exist"}
    role = user_info.role
    return render_template("sections.html", sections=sections, role = role)

@app.route("/librarianDashboard/revokeAccess/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def librarianDashboarRevokeAccess():
    
    book_issues = BookIssueModel.query\
        .join(BookModel, onclause=BookIssueModel.book_id == BookModel.id)\
        .with_entities(BookModel.name, BookIssueModel.uid).all()
    
    return render_template("revokeAccess.html", book_issues = book_issues)

@app.route("/revokeAccess/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def revokeAccess():
    id = request.args.get("id")
    username = request.args.get("username")

    user_login = UserLoginModel.query.filter_by(username = username).first()
    if not user_login:
        return {"message": "User Login not found"}

    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}, 404

    book_issue = BookIssueModel.query.filter_by(book_id=book.id, uid = user_login.id).first()
    if not book_issue:
        return {"message": "Book issue does not exist"}
    
    BookIssueModel.query.filter_by(book_id=book.id, uid = user_login.id).delete()
    db.session.commit()

    return redirect("/librarianDashboard/revokeAccess")

@app.route("/editSection/", methods = ["GET", "POST"])
@login_required
@check_role(role = "Librarian")
def editSection():
    id = request.args.get("id")
    section = SectionModel.query.filter_by(id = id).first()
    if request.method == "GET":
        return render_template("editSection.html", section = section)
    
    id = request.args.get("id")

    name = request.form.get("name")
    description = request.form.get("description")

    this_section = SectionModel.query.filter_by(id = id).first()
    if not this_section:
        return {"message": "Section not found"}

    section = SectionModel.query.filter_by(name = name).first()
    if section and not section.id == this_section.id:
        return {"message": "Section name already exists"}

    if name:
        this_section.name = name
    
    if description:
        this_section.description = description

    this_section.search_word = raw(this_section.name) + raw(this_section.description)

    db.session.commit()
    return redirect("/librarianDashboard/sections")

@app.route("/editBook/", methods = ["GET", "POST"])
@login_required
@check_role(role = "Librarian")
def editBook():
    if request.method == "GET":
        id = request.args.get("id")
        book = BookModel.query.filter_by(id = id).first()
        if not book:
            return {"message": "Book not found"}

        book_author = BookAuthorModel.query.filter_by(book_id = id).all()
        if not book_author:
            return {"message": "Book Author not found"}
        
        section = SectionModel.query.filter_by(id = book.section_id).first()
        if not section: 
            return {"message": "Section not found"}
        
        sections = SectionModel.query.all()

        return render_template("editBook.html", book = book, book_author = book_author, section = section, sections = sections)
    
    book_id = request.args.get("id")

    isbn = request.form.get("isbn")
    name = request.form.get("name")
    authors = request.form.get("authors")
    page_count = request.form.get("page_count")
    content_path = request.form.get("content_path")
    publisher = request.form.get("publisher")
    volume = request.form.get("volume")
    section_name = request.form.get("section_name")
    
    try:
        if page_count:
            page_count = int(page_count)
            if page_count < 1:
                return {"message": "Page count must be a positive integer"}
    except:
        return {"message": "Page count should be an integer"}

    book = BookModel.query.filter_by(id = book_id).first()
    if not book:
        return {"message": "Book does not exist"}

    if isbn:
        book.isbn = isbn

    if section_name:
        section = SectionModel.query.filter_by(name = section_name).first()
        if not section:
            return {"message": "Section does not exist"}
        book.section_id = section.id

    if name:
        book.name = name

    if authors:
        author_list = authors.split(',')
        BookAuthorModel.query.filter_by(book_id = book_id).delete()

        for author in author_list:
            author_search_word = raw(author)
            book_author = BookAuthorModel(book_id = book_id, author_name = author, search_word = author_search_word)  # type: ignore
            db.session.add(book_author)

    if page_count:
        book.page_count = page_count

    if content_path:
        book.content = content_path

    if publisher:
        book.publisher = publisher

    if volume: 
        book.volume = volume

    book.search_word = raw(book.isbn) + raw(book.name) + raw(book.publisher) + raw(section.name) + raw(str(book.volume)) + raw(str(book.page_count))

    db.session.commit()

    return redirect(f"/viewBooks/{section.id}")

@app.route("/removeSection/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def removeSection():
    id = request.args.get("id")
    if id == '0':
        return {"message": "Unassigned cannot be removed"}

    if not id:
        return {"message": "ID not provided"}
    
    section = SectionModel.query.filter_by(id = id).first()
    if not section:
        return {"message": "Section not found"}

    books = BookModel.query.filter_by(section_id = id).update({"section_id": 0})
    SectionModel.query.filter_by(id = id).delete()
    
    db.session.commit()

    return redirect("/librarianDashboard/sections")

@app.route("/removeBook/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def removeBook():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}
    
    section_id = book.section_id

    BookAuthorModel.query.filter_by(book_id = id).delete()
    BookRequestsModel.query.filter_by(book_id = id).delete()
    BookIssueModel.query.filter_by(book_id = id).delete()
    BookFeedbackModel.query.filter_by(book_id = id).delete()
    
    BookModel.query.filter_by(id = id).delete()
    db.session.commit()

    return redirect(f"/viewBooks/{section_id}")

@app.route("/librarianDashboard/viewBookStatus/", methods = ["GET"])
@login_required
@check_role(role = "Librarian")
def viewBookStatus():
    id = request.args.get("id")
    book_issues = BookIssueModel.query.filter_by(book_id = id).all()
    if not book_issues:
        return {"message": "No book issues exist"}
    
    book_and_users = BookIssueModel.query.filter_by(book_id = id)\
        .join(UserInfoModel, onclause = BookIssueModel.uid == UserInfoModel.uid)\
        .with_entities(BookIssueModel.book_id, BookIssueModel.uid, BookIssueModel.date_of_issue, 
                       BookIssueModel.date_of_return, UserInfoModel.first_name, UserInfoModel.last_name,
                       UserInfoModel.role).all()  # type: ignore
    if not book_and_users:
        return {"message": "User does not exist"}
    
    return render_template("viewBookStatus.html", id = id, book_and_users = book_and_users)

@app.route("/readBook/", methods = ["GET"])
@login_required
def readBook():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id = id).first()
    if not book:
        return {"message": "Book does not exist"}

    return render_template("/readBook.html", book = book)

@app.route("/readFeedback/", methods = ["GET"])
@login_required
def readFeedback():
    id = request.args.get("id")

    if not id:
        book_feedbacks = BookFeedbackModel.query\
            .join(BookModel, onclause=BookModel.id == BookFeedbackModel.book_id)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookFeedbackModel.uid, BookFeedbackModel.feedback).all()
        if not book_feedbacks:
            return {"message": "Book Feedback does not exist"}
    
        return render_template("readFeedback.html", book_feedbacks = book_feedbacks)
    else:
        book_feedbacks = BookFeedbackModel.query.filter_by(book_id = id)\
            .join(BookModel, onclause=BookModel.id == BookFeedbackModel.book_id)\
            .with_entities(BookModel.id, BookModel.isbn, BookModel.name, BookFeedbackModel.uid, BookFeedbackModel.feedback).all()
        
        if not book_feedbacks:
            return {"message": "Book Feedback does not exist"}

        return render_template("readSpecificFeedback.html", book_feedbacks = book_feedbacks)

@app.route("/sections/search/", methods=["GET"])
@login_required
def searchSection():
    
    search_word = request.args.get("search_word", default='')
    modified_search_word = '%'+raw(search_word)+'%'

    sections = SectionModel.query.filter(SectionModel.search_word.like(modified_search_word)).all()
    return render_template("search_sections.html", sections = sections)

@app.route("/viewBooks/<section_id>/search/", methods = ["GET"])
@login_required
def searchViewBooks(section_id):

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default='')
    books = findBooks(search_word, filter_section = section_id)

    user_info = UserInfoModel.query.filter_by(uid = current_user.id).first()
    if not user_info:
        return {"message": "User Info not found"}

    return render_template("search_viewBooks.html", books = books, book_authors = book_authors, role = user_info.role)

@app.route("/requestBooks/search/", methods = ["GET"])
@login_required
def searchRequestBooks():

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default ='')
    books = findBooks(search_word)

    return render_template("search_allBooks.html", books = books, book_authors = book_authors)

@app.route("/generalDashboard/books/search/", methods = ["GET"])
@login_required
def searchGeneralBooks():

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default ='')
    books = findBooks(search_word)

    book_requests = BookRequestsModel.query.filter_by(uid = current_user.id).all()
    book_issues = BookIssueModel.query.filter_by(uid = current_user.id).all()

    requested, issued = [], []
    for book in books:
        for req in book_requests:
            if book.id == req.book_id:
                requested.append(book)

        for issue in book_issues:
            if book.id == issue.book_id:
                issued.append(book)
    
    return render_template("search_generalBooks.html", requested = requested, issued = issued, book_authors = book_authors)

if __name__ == "__main__":
    app.run(debug=True)
