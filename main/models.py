# models.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from main import db  # Импортируем объект db из main/__init__.py

post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    votes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag', secondary='post_tags', back_populates='posts')
    views = db.Column(db.Integer, default=0)

    image_filename = db.Column(db.String(255))

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='posts')

    comments = db.relationship('Comment', back_populates='post', lazy=True, overlaps="comments,post")

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    post = db.relationship('Post', back_populates='comments', overlaps="comments,post")

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.Text, default='', nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar_url = db.Column(db.String(200), default='/static/default_avatar.png')

    description = db.Column(db.Text, default='', nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    reputation = db.Column(db.Integer, default=0)

    discord = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    membership_duration = db.Column(db.String(100), nullable=True)  # Например, "7 лет 9 месяцев"

    about_section = db.Column(db.Text, default='', nullable=True)   # Блок "о себе"
    welcome_section = db.Column(db.Text, default='', nullable=True) # Приветственный текст

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    posts = db.relationship('Post', secondary=post_tags, back_populates='tags')