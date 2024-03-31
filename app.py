from flask import (
    Flask,
    redirect,
    render_template,
    request,
    flash,
    send_from_directory,
    url_for,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from sqlalchemy import desc
from models import (
    BuyHistoryModel,
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
from datetime import datetime, timedelta, date
from typing import List
from werkzeug.utils import secure_filename

currentDirectory = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f'sqlite:///{os.path.join(currentDirectory, "db.sqlite3")}'
)
app.config["SECRET_KEY"] = "PsIK>@%=`TiDs$>"

db.init_app(app)

app.app_context().push()

login_manager.init_app(app)
app.register_blueprint(api_bp)

UPLOAD_FOLDER: str = "/static/books"
cwd = os.getcwd()
app.config["UPLOAD_FOLDER"] = os.getcwd() + UPLOAD_FOLDER

allowed_extensions = {"pdf"}

login_manager = LoginManager()

max_issue_time = 7


def raw(input: str) -> str:
    return input.lower().replace(" ", "")


def isFileAllowed(filename: str):
    return ("." in filename) and (filename.split(".")[-1].lower() in allowed_extensions)


def findBooks(search_word: str, filter_section=None):
    modified_search_word = "%" + raw(search_word) + "%"
    all_hits = []

    if filter_section:
        book_hits = (
            BookModel.query.filter(BookModel.search_word.like(modified_search_word))
            .filter_by(section_id=filter_section)
            .all()
        )

        author_hits = (
            BookAuthorModel.query.filter(
                BookAuthorModel.search_word.like(modified_search_word)
            )
            .join(BookModel, onclause=BookAuthorModel.book_id == BookModel.id)
            .filter_by(section_id=filter_section)
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
            )
            .all()
        )

        section_hits = (
            SectionModel.query.filter(
                SectionModel.search_word.like(modified_search_word)
            )
            .join(BookModel, onclause=SectionModel.id == BookModel.section_id)
            .filter_by(section_id=filter_section)
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
            )
            .all()
        )

    else:
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
        if current_user.is_authenticated:
            user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
            if user_info and user_info.role == "Librarian":
                return redirect("/librarianDashboard")

        return render_template("login.html", role="librarian")

    username = request.form.get("username")
    password = request.form.get("password")
    role = "Librarian"

    userLogin = UserLoginModel.query.filter_by(username=username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect(request.url)

    userInfo = UserInfoModel.query.filter_by(uid=userLogin.id).first()
    if userLogin and not userInfo:
        flash(f"There is no info regarding user {username}")
        return redirect(request.url)

    if userLogin and userLogin.password == password:
        if userInfo and userInfo.role != role:
            flash(f"Incorrect Username or Password")
            return redirect(request.url)
        else:
            login_user(userLogin)
    else:
        flash(f"Incorrect Username or Password")
        return redirect(request.url)

    return redirect(request.url)


@app.route("/generalLogin/", methods=["GET", "POST"])
def generalLogin():
    if request.method == "GET":
        if current_user.is_authenticated:
            user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
            if user_info and user_info.role == "General":
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
            flash(f"Incorrect Username or Password")
            return redirect("/generalLogin")
        else:
            login_user(userLogin)
    else:
        flash(f"Incorrect Username or Password")
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

    user_login = UserLoginModel.query.filter_by(username=username).first()
    if user_login:
        flash("Username already exists")
        return redirect(request.url)

    userLogin = UserLoginModel(username=username, password=password)  # type: ignore
    db.session.add(userLogin)
    db.session.commit()
    userInfo = UserInfoModel(uid=userLogin.id, first_name=first_name, last_name=last_name, role=role)  # type: ignore
    db.session.add(userInfo)
    db.session.commit()
    login_user(userLogin)
    return redirect("/generalDashboard")


@app.route("/librarianDashboard/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def librarianDashboard():
    section_count = 0
    sections = SectionModel.query.all()
    if sections:
        section_count = len(list(sections))

    book_count = 0
    books = BookModel.query.all()
    if books:
        book_count = len(list(books))

    request_count = 0
    requests = BookRequestsModel.query.all()
    if requests:
        request_count = len(list(requests))

    issue_count = 0
    issues = BookIssueModel.query.all()
    if issues:
        issue_count = len(list(issues))

    general_count = 0
    general_users = UserInfoModel.query.filter_by(role="General").all()
    if general_users:
        general_count = len(list(general_users))

    return render_template(
        "librarianDashboard.html",
        role="Librarian",
        section_count=section_count,
        book_count = book_count,
        request_count=request_count,
        issue_count=issue_count,
        general_count=general_count,
    )


@app.route("/librarianDashboard/sections/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def sections():
    sections = SectionModel.query.all()
    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info does not exist")
        return redirect(url_for("librarianDashboard"))
    role = user_info.role
    return render_template("/sections.html", sections=sections, role=role)


@app.route("/librarianDashboard/addSection/", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addSection():
    if request.method == "GET":
        return render_template("addSection.html")

    name = request.form.get("name")
    if not name:
        flash("Name not provided")
        return redirect(request.url)

    description = request.form.get("description")

    search_word = raw(name)
    if description:
        search_word += raw(description)

    section = SectionModel.query.filter_by(name=name).first()
    if section:
        flash(f"Section with name {name} already exists")
        return redirect(request.url)

    section = SectionModel(name=name, description=description, date_created=date.today(), search_word=search_word)  # type: ignore

    db.session.add(section)
    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/librarianDashboard/addBook", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def addBook():
    if request.method == "GET":
        section_id = request.args.get("section_id")
        if section_id:
            queried_section = SectionModel.query.filter_by(id=section_id).first()
            if not queried_section:
                flash("Section does not exist")
                return redirect(url_for("sections"))
        sections = SectionModel.query.all()
        return render_template("addBook.html", section_id=section_id, sections=sections)

    section_id = request.args.get("section_id")

    isbn = request.form.get("isbn")
    book_name = request.form.get("book_name")
    page_count = request.form.get("page_count")
    book_file = request.files["book_file"]
    publisher = request.form.get("publisher")
    volume = request.form.get("volume")
    author_names = request.form.get("author_names")
    price = request.form.get("price")

    if not book_file:
        flash("Book file not given")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    if not book_file.filename:
        flash("No file name")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    filename = secure_filename(book_file.filename)

    if not isFileAllowed(filename):
        flash("This file type is not allowed")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    content_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if os.path.exists(content_path):
        book = BookModel.query.filter_by(content="books/" + filename).first()
        if not book:
            flash(
                "There is a book pdf which exists but there is no book with the corresponding path.\
                     Need to manually remove the pdf"
            )
            return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

        flash(
            f"This book PDF already exists and is referenced by book_id: {book.id} with name: {book.name}"
        )
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    try:
        if page_count:
            page_count = int(page_count)
            if page_count < 1:
                flash("Page count must be a positive integer")
                return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    except ValueError:
        flash("Page count should be an integer")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")
    except Exception as e:
        flash(str(e))
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    if section_id != "None":
        section = SectionModel.query.filter_by(id=section_id).first()
    else:
        section_name = request.form.get("section_name")
        section = SectionModel.query.filter_by(name=section_name).first()

    if not section:
        flash("Section does not exist")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    if not author_names:
        flash("Author names not given")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    author_names_list: List[str] = [
        author_name.strip() for author_name in author_names.split(",")
    ]

    if not book_name:
        flash("Book name not provided")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")
    if not isbn:
        flash("ISBN not provided")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    if not publisher:
        flash("Publisher not provided")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    book = BookModel.query.filter_by(isbn=isbn).first()

    if book:
        flash("Book already exists")
        return redirect(f"/librarianDashboard/addBook?section_id={section_id}")

    search_word: str = (
        raw(isbn)
        + raw(book_name)
        + raw(publisher)
        + raw(section.name)
        + raw(str(volume))
        + raw(str(page_count))
    )

    book = BookModel(
        isbn=isbn,
        name=book_name,
        page_count=page_count,
        content="books/" + filename,
        publisher=publisher,
        volume=volume,
        section_id=section.id,
        search_word=search_word,
        price=price,
    )  # type: ignore
    db.session.add(book)
    db.session.commit()

    for author_name in author_names_list:
        author_search_word: str = raw(author_name)
        author = BookAuthorModel(book_id=book.id, author_name=author_name, search_word=author_search_word)  # type: ignore
        db.session.add(author)
    db.session.commit()
    book_file.save(content_path)

    return redirect(f"/sections/{section.id}")


# Don't restrict by role since used by both users
@app.route("/sections/<section_id>/", methods=["GET"])
@login_required
def viewBooks(section_id):

    book_authors = get_all_book_authors()

    section = SectionModel.query.filter_by(id=section_id).first()

    if not section:
        flash("Section not found")
        return redirect(url_for("sections"))

    books = BookModel.query.filter_by(section_id=section.id).all()

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info does not exist")
        return redirect("/")

    print(books)

    book_issues = BookIssueModel.query.filter_by(uid=current_user.id).all()
    book_requests = BookRequestsModel.query.filter_by(uid=current_user.id).all()

    my_books = []
    for book_issue in book_issues:
        my_books.append(book_issue)

    for book_request in book_requests:
        my_books.append(book_request)

    return render_template(
        "viewBooks.html",
        section_id=section.id,
        books=books,
        role=user_info.role,
        book_authors=book_authors,
        my_books=my_books,
    )


@app.route("/generalDashboard/", methods=["GET"])
@login_required
@check_role(role="General")
def generalDashboard():

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info does not exist")
        return redirect("/")

    book_issues = (
        BookIssueModel.query
        .filter_by(uid=current_user.id)
        .join(
            BookModel, onclause=BookIssueModel.book_id == BookModel.id
        )
        .with_entities(BookIssueModel.date_of_return, BookModel.name)
        .all()
    )
    issue_count = 0
    if book_issues:
        issue_count = len(list(book_issues))

    request_count = 0
    book_requests = BookRequestsModel.query.filter_by(uid=current_user.id).all()
    if book_requests:
        request_count = len(list(book_requests))

    return render_template(
        "generalDashboard.html",
        name=user_info.first_name,
        role=user_info.role,
        issue_count=issue_count,
        book_issues=book_issues,
        request_count=request_count,
    )


@app.route("/generalDashboard/requestBooks/", methods=["GET"])
@check_role(role="General")
@login_required
def requestBooks():

    book_authors = get_all_book_authors()

    book_requests = BookRequestsModel.query.filter_by(uid=current_user.id).all()
    book_issues = BookIssueModel.query.filter_by(uid=current_user.id).all()

    issued_book_ids = [book_request.book_id for book_request in book_requests]
    issued_book_ids.extend([book_issue.book_id for book_issue in book_issues])
    print(issued_book_ids)
    books = (
        db.session.query(BookModel, SectionModel)
        .join(SectionModel, onclause=SectionModel.id == BookModel.section_id)
        .all()
    )
    return render_template(
        "allBooks.html",
        books=books,
        issued_book_ids=issued_book_ids,
        book_authors=book_authors,
    )


@app.route("/requestBook/", methods=["GET", "POST"])
@login_required
@check_role(role="General")
def requestBook():

    if request.method == "GET":
        id = request.args.get("id")

        book = BookModel.query.filter_by(id=id).first()
        if not book:
            flash("Book does not exist")
            return redirect(url_for("requestBooks"))

        request_book = BookRequestsModel.query.filter_by(
            book_id=id, uid=current_user.id
        ).first()
        if request_book:
            flash("Book request already exists")
            return redirect("/generalDashboard/requestBooks/")

        issue_book = BookIssueModel.query.filter_by(
            book_id=id, uid=current_user.id
        ).first()
        if issue_book:
            flash("Book has already been issued")
            return redirect("/generalDashboard/requestBooks/")

        book_request = BookRequestsModel.query.filter_by(uid=current_user.id).all()
        book_issue = BookIssueModel.query.filter_by(uid=current_user.id).all()
        if (len(book_request) + len(book_issue)) >= 5:
            flash("You can only request/issue 5 books at once")
            return redirect("/generalDashboard/requestBooks/")

        return render_template("requestForm.html", id=id)

    id = request.args.get("id")

    try:
        issue_time = int(request.form.get("issue_time", 7))
    except Exception as e:
        flash(str(e))
        return redirect(f"/requestBook?id={id}")

    if not (1 <= issue_time <= max_issue_time):
        flash("Issue time should be in range (1,7)")
        return redirect(f"/requestBook?id={id}")

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("requestBooks"))

    book_request = BookRequestsModel.query.filter_by(
        book_id=book.id, uid=current_user.id
    ).first()
    if book_request:
        flash("Book request already exists")
        return redirect(url_for("requestBooks"))

    book_issue = BookIssueModel.query.filter_by(
        book_id=book.id, uid=current_user.id
    ).first()
    if book_issue:
        flash("Book has already been issued")
        return redirect(url_for("requestBooks"))

    book_request = BookRequestsModel(book_id=book.id, uid=current_user.id, date_of_request=date.today(), issue_time=issue_time)  # type: ignore
    db.session.add(book_request)
    db.session.commit()

    return redirect("/generalDashboard/requestBooks")


@app.route("/generalDashboard/books/", methods=["GET", "POST"])
@login_required
@check_role(role="General")
def generalBooks():
    if request.method == "GET":

        book_authors = get_all_book_authors()

        requested = (
            db.session.query(BookRequestsModel, BookModel)
            .join(BookRequestsModel, onclause=BookRequestsModel.book_id == BookModel.id)
            .filter_by(uid=current_user.id)
            .all()
        )
        issued = (
            db.session.query(BookIssueModel, BookModel)
            .join(BookIssueModel, onclause=BookIssueModel.book_id == BookModel.id)
            .filter_by(uid=current_user.id)
            .all()
        )

        for issued_book, book in issued:
            if issued_book.date_of_return < date.today():
                BookIssueModel.query.filter_by(
                    book_id=issued_book.book_id, uid=current_user.id
                ).delete()

        db.session.commit()
        issued = (
            db.session.query(BookIssueModel, BookModel)
            .join(BookIssueModel, onclause=BookIssueModel.book_id == BookModel.id)
            .filter_by(uid=current_user.id)
            .all()
        )

        return render_template(
            "generalBooks.html",
            issued=issued,
            requested=requested,
            book_authors=book_authors,
            role="General",
        )

    return ""


@app.route("/librarianDashboard/viewRequests/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def viewRequests():
    book_requests = (
        BookRequestsModel.query.join(
            UserInfoModel, onclause=UserInfoModel.uid == BookRequestsModel.uid
        )
        .join(BookModel, onclause=BookModel.id == BookRequestsModel.book_id)
        .with_entities(
            BookModel.id,
            BookModel.name,
            BookModel.isbn,
            BookRequestsModel.date_of_request,
            BookRequestsModel.issue_time,
            UserInfoModel.first_name,
            UserInfoModel.last_name,
            UserInfoModel.uid,
        )
        .all()
    )
    return render_template("viewRequests.html", requests=book_requests)


@app.route("/librarianDashboard/viewRequests/dealWithRequest/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def dealWithRequest():
    id = request.args.get("id")
    uid = request.args.get("uid")
    issue_time = request.args.get("issue_time")
    accept = request.args.get("accept")

    if accept not in ("0", "1"):
        flash("accept should be in (0,1)")
        return redirect(url_for("viewRequests"))

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("viewRequests"))

    if accept == "1":
        # Accept book

        book_issue = BookIssueModel.query.filter_by(book_id=book.id, uid=uid).first()
        if book_issue:
            flash("Book Issue already exists")
            return redirect(url_for("viewRequests"))

        book_issue = BookIssueModel(book_id=book.id, uid=uid, date_of_issue=date.today(), date_of_return=date.today() + timedelta(int(issue_time)))  # type: ignore

        BookRequestsModel.query.filter_by(book_id=book.id, uid=uid).delete()

        db.session.add(book_issue)
        db.session.commit()

        return redirect("/librarianDashboard/viewRequests")

    else:
        # Reject book
        BookRequestsModel.query.filter_by(book_id=book.id, uid=uid).delete()
        db.session.commit()
        return redirect("/librarianDashboard/viewRequests")


@app.route("/returnBook/", methods=["GET"])
@login_required
@check_role(role="General")
def returnBook():
    id = request.args.get("id")

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("generalBooks"))

    book_issue = BookIssueModel.query.filter_by(uid=current_user.id, book_id=book.id)
    if not book_issue:
        flash("Book issue does not exist")
        return redirect(url_for("generalBooks"))

    BookIssueModel.query.filter_by(uid=current_user.id, book_id=book.id).delete()
    db.session.commit()

    return redirect(f"/feedback?id={id}")


@app.route("/feedback/", methods=["GET", "POST"])
@login_required
@check_role(role="General")
def feedback():
    if request.method == "GET":
        id = request.args.get("id")
        book = BookModel.query.filter_by(id=id).first()
        if not book:
            flash("Book does not exist")
            return redirect(url_for("generalDashboard"))
        return render_template("feedback.html", book=book)

    id = request.args.get("id")
    feedback = request.form.get("feedback")
    rating = request.form.get("rating")

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("generalDashboard"))

    BookFeedbackModel.query.filter_by(uid=current_user.id, book_id=book.id).delete()

    book_feedback = BookFeedbackModel(uid=current_user.id, book_id=book.id, feedback=feedback, rating=rating)  # type: ignore
    db.session.add(book_feedback)
    db.session.commit()

    return redirect("/generalDashboard/books")


@app.route("/generalDashboard/sections/", methods=["GET"])
@login_required
@check_role(role="General")
def generalViewSections():
    sections = SectionModel.query.all()
    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info does not exist")
        return redirect("/")

    role = user_info.role
    return render_template("sections.html", sections=sections, role=role)


@app.route("/librarianDashboard/revokeAccess/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def librarianDashboarRevokeAccess():

    book_issues = (
        BookIssueModel.query.join(
            BookModel, onclause=BookIssueModel.book_id == BookModel.id
        )
        .join(UserInfoModel, onclause=UserInfoModel.uid == BookIssueModel.uid)
        .with_entities(
            BookIssueModel.book_id,
            BookModel.name,
            BookIssueModel.uid,
            UserInfoModel.first_name,
            UserInfoModel.last_name,
        )
        .all()
    )

    return render_template("revokeAccess.html", book_issues=book_issues)


@app.route("/revokeAccess/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def revokeAccess():
    id = request.args.get("id")
    uid = request.args.get("uid")

    user_login = UserLoginModel.query.filter_by(id=uid).first()
    if not user_login:
        flash("User Login not found")
        return redirect("/")

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("librarianDashboarRevokeAccess"))

    book_issue = BookIssueModel.query.filter_by(
        book_id=book.id, uid=user_login.id
    ).first()
    if not book_issue:
        flash("Book issue does not exist")
        return redirect(url_for("librarianDashboarRevokeAccess"))

    BookIssueModel.query.filter_by(book_id=book.id, uid=user_login.id).delete()
    db.session.commit()

    return redirect("/librarianDashboard/revokeAccess")


@app.route("/librarianDashboard/editSection/", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def editSection():
    id = request.args.get("id")
    section = SectionModel.query.filter_by(id=id).first()

    if not section:
        flash("Section not found")
        return redirect(url_for("sections"))

    if request.method == "GET":
        return render_template("editSection.html", section=section)

    id = request.args.get("id")

    name = request.form.get("name")
    description = request.form.get("description")

    this_section = SectionModel.query.filter_by(id=id).first()
    if not this_section:
        flash("Section not found")
        return redirect(url_for("sections"))

    section = SectionModel.query.filter_by(name=name).first()
    if section and not section.id == this_section.id:
        flash("Section name already exists")
        return redirect(f"/librarianDashboard/editSection?id={id}")

    if name:
        this_section.name = name

    if description:
        this_section.description = description

    this_section.search_word = raw(this_section.name) + raw(this_section.description)

    db.session.commit()
    return redirect("/librarianDashboard/sections")


@app.route("/librarianDashboard/editBook/", methods=["GET", "POST"])
@login_required
@check_role(role="Librarian")
def editBook():
    if request.method == "GET":
        id = request.args.get("id")
        book = BookModel.query.filter_by(id=id).first()
        if not book:
            flash("Book not found")
            return redirect(url_for("sections"))

        book_author = BookAuthorModel.query.filter_by(book_id=id).all()
        if not book_author:
            flash("Book Author not found")
            return redirect(f"/sections/{book.section_id}")

        section = SectionModel.query.filter_by(id=book.section_id).first()
        if not section:
            flash("Section not found")
            return redirect(f"/sections/{book.section_id}")

        sections = SectionModel.query.all()

        return render_template(
            "editBook.html",
            book=book,
            book_author=book_author,
            section=section,
            sections=sections,
        )

    book_id = request.args.get("id")

    isbn = request.form.get("isbn")
    name = request.form.get("name")
    authors = request.form.get("authors")
    page_count = request.form.get("page_count")
    book_file = request.files["book_file"]
    publisher = request.form.get("publisher")
    volume = request.form.get("volume")
    section_name = request.form.get("section_name")

    content_path = None
    if book_file:
        if book_file.filename:
            filename = secure_filename(book_file.filename)

            if not isFileAllowed(filename):
                flash("This file type is not allowed")
                return redirect(f"/librarianDashboard/editBook?id={book_id}")

            content_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(content_path):
                book = BookModel.query.filter_by(content="books/" + filename).first()
                if not book:
                    flash(
                        "There is a book pdf which exists but there is no book with the corresponding path.\
                            Need to manually remove the pdf"
                    )
                    return redirect(f"/librarianDashboard/editBook?id={book_id}")

                flash(
                    f"This book PDF already exists and is referenced by book_id: {book.id} with name: {book.name}"
                )
                return redirect(f"/librarianDashboard/editBook?id={book_id}")

    try:
        if page_count:
            page_count = int(page_count)
            if page_count < 1:
                flash("Page count must be a positive integer")
                return redirect(f"/librarianDashboard/editBook?id={book_id}")

    except:
        flash("Page count should be an integer")
        return redirect(f"/librarianDashboard/editBook?id={book_id}")

    book = BookModel.query.filter_by(id=book_id).first()
    if not book:
        flash("Book does not exist")
        return redirect(f"/librarianDashboard/editBook?id={book_id}")

    if isbn:
        book.isbn = isbn

    if section_name:
        section = SectionModel.query.filter_by(name=section_name).first()
        if not section:
            flash("Section does not exist")
            return redirect(f"/librarianDashboard/editBook?id={book_id}")
        book.section_id = section.id

    if name:
        book.name = name

    if authors:
        author_list = authors.split(",")
        BookAuthorModel.query.filter_by(book_id=book_id).delete()

        for author in author_list:
            author_search_word = raw(author)
            book_author = BookAuthorModel(book_id=book_id, author_name=author, search_word=author_search_word)  # type: ignore
            db.session.add(book_author)

    if page_count:
        book.page_count = page_count

    if content_path:
        old_content = book.content
        try:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_content[6:])
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

    book.search_word = (
        raw(book.isbn)
        + raw(book.name)
        + raw(book.publisher)
        + raw(section.name)
        + raw(str(book.volume))
        + raw(str(book.page_count))
    )

    db.session.commit()

    return redirect(f"/sections/{section.id}")


@app.route("/librarianDashboard/removeSection/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def removeSection():
    id = request.args.get("id")
    if id == "0":
        flash("Unassigned cannot be removed")
        return redirect(url_for("sections"))

    if not id:
        flash("ID not provided")
        return redirect(url_for("sections"))

    section = SectionModel.query.filter_by(id=id).first()
    if not section:
        flash("Section not found")
        return redirect(url_for("sections"))

    books = BookModel.query.filter_by(section_id=id).update({"section_id": 0})
    SectionModel.query.filter_by(id=id).delete()

    db.session.commit()

    return redirect("/librarianDashboard/sections")


@app.route("/librarianDashboard/removeBook/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def removeBook():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("sections"))

    section_id = book.section_id

    old_content = book.content
    try:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_content[6:])
        os.remove(old_path)
    except Exception as e:
        return str(e)

    BookAuthorModel.query.filter_by(book_id=id).delete()
    BookRequestsModel.query.filter_by(book_id=id).delete()
    BookIssueModel.query.filter_by(book_id=id).delete()
    BookFeedbackModel.query.filter_by(book_id=id).delete()

    BookModel.query.filter_by(id=id).delete()
    db.session.commit()

    return redirect(f"/sections/{section_id}")


@app.route("/librarianDashboard/viewBookStatus/", methods=["GET"])
@login_required
@check_role(role="Librarian")
def viewBookStatus():
    id = request.args.get("id")

    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("librarianDashboard"))

    book_issues = BookIssueModel.query.filter_by(book_id=id).all()

    book_and_users = (
        BookIssueModel.query.filter_by(book_id=id)
        .join(UserInfoModel, onclause=BookIssueModel.uid == UserInfoModel.uid)
        .with_entities(
            BookIssueModel.book_id,
            BookIssueModel.uid,
            BookIssueModel.date_of_issue,
            BookIssueModel.date_of_return,
            UserInfoModel.first_name,
            UserInfoModel.last_name,
            UserInfoModel.role,
        )
        .all()
    )  # type: ignore

    return render_template("viewBookStatus.html", id=id, book_and_users=book_and_users)


@app.route("/readBook/", methods=["GET"])
@login_required
def readBook():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book does not exist")
        return redirect(url_for("sections"))

    return render_template("/readBook.html", book=book)


@app.route("/readFeedback/", methods=["GET"])
@login_required
def readFeedback():
    id = request.args.get("id")

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info not found")
        return redirect("/")

    role = user_info.role

    if id:
        book = BookModel.query.filter_by(id=id).first()
        if not book:
            flash("Book does not exist")
            return redirect(f"/{user_info.role.lower()}Dashboard")

    if not id:
        book_feedbacks = (
            BookFeedbackModel.query.join(
                BookModel, onclause=BookModel.id == BookFeedbackModel.book_id
            )
            .join(UserLoginModel, onclause=UserLoginModel.id == BookFeedbackModel.uid)
            .with_entities(
                BookModel.id,
                BookModel.isbn,
                BookModel.name,
                BookFeedbackModel.uid,
                BookFeedbackModel.feedback,
                BookFeedbackModel.rating,
                UserLoginModel.username,
            )
            .all()
        )

        return render_template(
            "readFeedback.html", book_feedbacks=book_feedbacks, role=role
        )
    else:
        book_feedbacks = (
            BookFeedbackModel.query.filter_by(book_id=id)
            .join(BookModel, onclause=BookModel.id == BookFeedbackModel.book_id)
            .join(UserLoginModel, onclause=UserLoginModel.id == BookFeedbackModel.uid)
            .with_entities(
                BookModel.id,
                BookModel.isbn,
                BookModel.name,
                BookFeedbackModel.uid,
                BookFeedbackModel.feedback,
                BookFeedbackModel.rating,
                UserLoginModel.username,
            )
            .all()
        )

        return render_template(
            "readSpecificFeedback.html", book_feedbacks=book_feedbacks, role=role
        )


@app.route("/sections/search/", methods=["GET"])
@login_required
def searchSection():

    search_word = request.args.get("search_word", default="")
    search_target = request.args.get("search_target", default="sections")

    if search_target not in ("books", "sections"):
        flash("Search target should be either 'books' or 'sections'")
        return redirect(url_for("sections"))

    if search_target == "books":
        return redirect(f"/requestBooks/search?search_word={search_word}")

    modified_search_word = "%" + raw(search_word) + "%"

    sections = SectionModel.query.filter(
        SectionModel.search_word.like(modified_search_word)
    ).all()

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        return redirect("/")

    return render_template(
        "search_sections.html", sections=sections, role=user_info.role
    )


@app.route("/viewBooks/<section_id>/search/", methods=["GET"])
@login_required
def searchViewBooks(section_id):

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default="")
    books = findBooks(search_word, filter_section=section_id)

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User Info not found")
        return redirect("/")

    book_issues = BookIssueModel.query.filter_by(uid=current_user.id).all()
    book_requests = BookRequestsModel.query.filter_by(uid=current_user.id).all()

    my_books = []
    for book_issue in book_issues:
        my_books.append(book_issue)

    for book_request in book_requests:
        my_books.append(book_request)

    return render_template(
        "search_viewBooks.html",
        books=books,
        book_authors=book_authors,
        role=user_info.role,
        my_books=my_books,
    )


@app.route("/requestBooks/search/", methods=["GET"])
@login_required
def searchRequestBooks():

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default="")
    books = findBooks(search_word)

    user_info = UserInfoModel.query.filter_by(uid=current_user.id).first()
    if not user_info:
        flash("User info does not exist")
        return redirect("/")

    return render_template(
        "search_allBooks.html",
        books=books,
        book_authors=book_authors,
        role=user_info.role,
    )


@app.route("/generalDashboard/books/search/", methods=["GET"])
@login_required
@check_role(role="General")
def searchGeneralBooks():

    book_authors = get_all_book_authors()

    search_word = request.args.get("search_word", default="")
    books = findBooks(search_word)

    book_requests = BookRequestsModel.query.filter_by(uid=current_user.id).all()
    book_issues = BookIssueModel.query.filter_by(uid=current_user.id).all()

    requested, issued = [], []
    for book in books:
        for req in book_requests:
            if book.id == req.book_id:
                requested.append(book)

        for issue in book_issues:
            if book.id == issue.book_id:
                issued.append(book)

    return render_template(
        "search_generalBooks.html",
        requested=requested,
        issued=issued,
        book_authors=book_authors,
        role="General",
    )


@app.route("/buyBook", methods=["GET", "POST"])
@login_required
@check_role(role="General")
def buyBook():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book not found")
        return redirect(f"/buyBook?id={id}")

    if request.method == "GET":
        return render_template("buyBook.html", book=book)

    buy_history = BuyHistoryModel.query.filter_by(
        uid=current_user.id, book_id=book.id
    ).first()
    if buy_history:
        flash("You have already bought this book")
    else:
        buy_history = BuyHistoryModel(uid=current_user.id, book_id=book.id, bought_at=datetime.now())  # type: ignore
        db.session.add(buy_history)
        db.session.commit()

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        book.content.replace("books/", "", 1),
        as_attachment=True,
    )


@app.route("/download")
@login_required
@check_role(role="Librarian")
def route():
    id = request.args.get("id")
    book = BookModel.query.filter_by(id=id).first()
    if not book:
        flash("Book not found")
        return redirect(f"/download?id={id}")

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        book.content.replace("books/", "", 1),
        as_attachment=True,
    )


if __name__ == "__main__":
    app.run(debug=True)
