from flask import Flask, redirect, render_template, request,  flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from models import db, UserLoginModel, UserInfoModel, SectionModel, BookModel, BookAuthorModel, BookRequestsModel, BookIssueModel, BookFeedbackModel
import os
from blueprints.api import api_bp, login_manager

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

    return redirect("userInfo")

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

    return redirect("userInfo")

@app.route('/logout', methods = ['GET'])
def logout():
    logout_user()
    return redirect("/")

@app.route('/userInfo', methods = ['GET'])
def userInfo():
    return render_template('userInfo.html', username = current_user.username, password = current_user.password)



if __name__ == "__main__":
    app.run(debug=True)
