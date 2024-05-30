from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

app = Flask(__name__)
app.config['SECRET_KEY'] = '260ff976dbb793af832554aff4cae3f1'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category= 'info'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'blueyblog@gmail.com'
app.config['MAIL_PASSWORD'] = 'krea lfqc abzg scmv'
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)


from Bluey_blog import routes
with app.app_context():
    db.create_all()
