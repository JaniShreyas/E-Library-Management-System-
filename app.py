from flask import Flask, redirect, render_template, request,  flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from sqlalchemy import desc
from models import db, UserLoginModel, UserInfoModel, SectionModel, BookModel, BookAuthorModel, BookRequestsModel, BookIssueModel, BookFeedbackModel
import os
from blueprints.api import api_bp, check_role, login_manager, check_role
from datetime import datetime, timedelta

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

@app.route('/', methods = ['GET'])
def home():
    return render_template("home.html")

@app.route('/librarianLogin', methods = ['GET', 'POST'])
def librarianLogin():
    if request.method == "GET":
        return render_template('login.html', role = "librarian")
    
    username = request.form.get("username")
    password = request.form.get("password")
    role = "Librarian"

    userLogin = UserLoginModel.query.filter_by(username = username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/librarianLogin")
    
    userInfo = UserInfoModel.query.filter_by(username = username).first()
    if userLogin and  not userInfo:
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

    return redirect("/dashboard/sections")

@app.route('/generalLogin', methods = ['GET', 'POST'])
def generalLogin():
    if request.method == "GET":
        return render_template('login.html', role = "general")
    
    username = request.form.get("username")
    password = request.form.get("password")
    role = "General"

    userLogin = UserLoginModel.query.filter_by(username = username).first()
    if not userLogin:
        flash(f"User with username {username} does not exist")
        return redirect("/generalLogin")
    
    userInfo = UserInfoModel.query.filter_by(username = username).first()
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

    return redirect("/dashboard/sections")

@app.route('/logout', methods = ['GET'])
def logout():
    logout_user()
    return redirect("/")

@app.route('/addUser', methods=['GET', 'POST'])
def addUser():
    if request.method == 'GET':
        return render_template('addUser.html')
    
    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    role = "General"

    userLogin = UserLoginModel(username = username, password = password)  #type: ignore
    userInfo = UserInfoModel(username = username, first_name = first_name, last_name = last_name, role = role)  #type: ignore
    db.session.add(userLogin)
    db.session.add(userInfo)
    db.session.commit()

    return redirect('/dashboard/sections')

@app.route('/dashboard/sections', methods = ['GET'])
@login_required
def sections():
    sections = SectionModel.query.all()
    return render_template('sections.html', sections = sections)

@app.route('/addSection', methods = ['GET', 'POST'])
@login_required
@check_role(role = 'Librarian')
def addSection():
    if request.method == 'GET':
        return render_template('addSection.html')
    
    name = request.form.get('name')
    description = request.form.get('description')
    section = SectionModel(name = name, description = description, date_created = datetime.now())  #type: ignore

    db.session.add(section)
    db.session.commit()

    return redirect('/dashboard/sections')

if __name__ == "__main__":
    app.run(debug=True)
