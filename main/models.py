# models.py
from datetime import datetime
from typing import Self
from sqlalchemy import func
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', backref='comments')
    post = db.relationship('Post', back_populates='comments', overlaps="comments,post")

    votes = db.relationship('CommentVote', back_populates='comment', cascade='all, delete-orphan')


class CommentVote(db.Model):
    __tablename__ = 'comment_vote'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote = db.Column(db.Integer, nullable=False)  # 1 — лайк, -1 — дизлайк

    comment = db.relationship('Comment', back_populates='votes')
    user = db.relationship('User', back_populates='comment_votes')


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.Text, default='', nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar_url = db.Column(db.String(255), default='default_avatar.png')
    preferred_lang = db.Column(db.String(10), default='uk', nullable=False)

    description = db.Column(db.Text, default='', nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    reputation = db.Column(db.Integer, default=0)

    discord = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    membership_duration = db.Column(db.String(100), nullable=True)  # Например, "7 лет 9 месяцев"

    about_section = db.Column(db.Text, default='', nullable=True)   # Блок "о себе"
    welcome_section = db.Column(db.Text, default='', nullable=True) # Приветственный текст
    comment_votes = db.relationship('CommentVote', back_populates='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

    def calculate_reputation(self):
        from main import db
        from sqlalchemy import func
        from main.models import PostVote, CommentVote, Post, Comment

        post_votes_sum = db.session.query(func.coalesce(func.sum(PostVote.value), 0))\
            .join(Post).filter(Post.author_id == self.id).scalar()

        comment_votes_sum = db.session.query(func.coalesce(func.sum(CommentVote.vote), 0))\
            .join(Comment).filter(Comment.user_id == self.id).scalar()

        self.reputation = post_votes_sum + comment_votes_sum

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    posts = db.relationship('Post', secondary=post_tags, back_populates='tags')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)


class PostVote(db.Model):
    __tablename__ = 'post_vote'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    value = db.Column(db.Integer, nullable=False)  # 1 = like, -1 = dislike

    post = db.relationship('Post', backref='votes_detail')
    user = db.relationship('User', backref='votes')