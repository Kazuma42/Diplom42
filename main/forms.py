from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from flask_wtf.file import FileAllowed

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(6, 128)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class EditProfileForm(FlaskForm):
    about = TextAreaField("Про себе", validators=[Optional()])
    location = StringField("Місто", validators=[Optional()])
    discord = StringField("Discord", validators=[Optional()])
    email = StringField("Email", validators=[Email(), Optional()])
    welcome = TextAreaField("Привітання", validators=[Optional()])
    membership_duration = StringField("Стаж", validators=[Optional()])
    avatar = FileField("Аватар", validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg'], 'Тільки зображення!')])
    
class PostForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=100)])
    text = TextAreaField('Текст', validators=[DataRequired()])
    tags = StringField('Теги')
    image = FileField('Изображение', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Только картинки!')])
    submit = SubmitField('Опубликовать')