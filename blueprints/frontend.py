from flask import Blueprint, render_template

frontend_bp = Blueprint('frontend', __name__, template_folder='templates')

@frontend_bp.route("/login", methods = ['GET'])
def librarianLogin():
    return render_template('login.html')