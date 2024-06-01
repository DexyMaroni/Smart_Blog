from datetime import datetime, timezone
import json
from time import time
from itsdangerous import URLSafeSerializer, TimestampSigner
from Bluey_blog import db, login_manager, app
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='main_default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref = 'author', lazy = True)
    comments = db.relationship('Comment', backref='author', lazy=True) # Update

    def get_reset_token(self, expires_sec=3600):
        s = TimestampSigner(app.config['SECRET_KEY'])
        token_data = json.dumps({'user_id': self.id, 'exp': time() + expires_sec})
        return s.sign(token_data.encode('utf-8')).decode('utf-8')
    
    @staticmethod
    def verify_reset_token(token):
        ''' This function verifies a token.

            Args:
                token: A encoded bit of data.

            Returns:
                Info of the decoded user.
        ''' 
        s = TimestampSigner(app.config['SECRET_KEY'])
        try:
            token = s.unsign(token, max_age=3600)
            user_id = json.loads(token)['user_id']

        except:
            return None
        
        return User.query.get(user_id)

    def __repr__(self):
        return f"User ('{self.username}', '{self.email}', '{self.image_file}')"



class Post(db.Model):
    ''' A data base model that stores infomation related to a users post '''
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    
    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"
    
    
class Comment(db.Model): # Update
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    
    def __repr__(self) -> str:
        return f"Comment('{self.content}', '{self.date_posted}')"