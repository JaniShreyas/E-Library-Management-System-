from flask import Flask
from models import db
import os
from blueprints.api import api_bp, login_manager
from blueprints.frontend import frontend_bp

currentDirectory = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f'sqlite:///{os.path.join(currentDirectory, "db.sqlite3")}'
app.config["SECRET_KEY"] = "PsIK>@%=`TiDs$>"

db.init_app(app)

app.app_context().push()

login_manager.init_app(app)
app.register_blueprint(api_bp)
app.register_blueprint(frontend_bp)

if __name__ == "__main__":
    app.run(debug=True)
