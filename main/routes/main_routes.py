from datetime import datetime, timedelta
import random
import os
from flask import Blueprint, abort, app, current_app, render_template, request, redirect, url_for
from sqlalchemy import func
from main.forms import EditProfileForm
from main.models import Post, Comment, db, User, post_tags
import traceback
from flask import flash
#from main.models import check_password_hash
#from main.models import generate_password_hash
from flask import session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from main.models import Tag
from flask import g




ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


main_bp = Blueprint(
    'main',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)


@main_bp.route("/")
@main_bp.route('/main.index')
def index():
    period = request.args.get('period', 'all')
    now = datetime.utcnow()

    if period == 'month':
        date_from = now - timedelta(days=30)
        posts = Post.query.filter(Post.created_at >= date_from).order_by(Post.created_at.desc()).all()
        empty_message = "Немає постів за останній місяць."
    elif period == 'year':
        date_from = now - timedelta(days=365)
        posts = Post.query.filter(Post.created_at >= date_from).order_by(Post.created_at.desc()).all()
        empty_message = "Немає постів за останній рік."
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()
        empty_message = "Немає постів."

    return render_template('index.html', posts=posts, current_filter=period, empty_message=empty_message)

@main_bp.route('/main.posts')
def posts():
    posts = Post.query.order_by(db.func.random()).all()  
    return render_template('posts.html', posts=posts)


@main_bp.route("/main.create", methods=['POST', 'GET'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']
        tags_input = request.form.get('tags', '')  
        image = request.files.get('image')
        filename = None

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            image.save(os.path.join(upload_folder, filename))
        elif image and image.filename != '':
            flash("Невірний формат зображення", 'danger')
            return redirect(request.url)

        tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
        tag_objects = []
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name, description="")  
                db.session.add(tag)
            tag_objects.append(tag)

        post = Post(
            title=title,
            text=text,
            tags=tag_objects, 
            author=current_user,
            image_filename=filename
        )

        try:
            db.session.commit()  
            db.session.add(post)
            db.session.commit()
            flash('Питання успішно опубліковано!', 'success')
            return redirect('/')
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return f'Помилка при додані питання: {e}'

    return render_template('create.html')
    

@main_bp.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)

    
    post.views = (post.views or 0) + 1
    db.session.commit()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'like':
            post.likes = (post.likes or 0) + 1
            post.votes = (post.votes or 0) + 1 
        elif action == 'dislike':
            post.dislikes = (post.dislikes or 0) + 1
            post.votes = (post.votes or 0) + 1

        comment_text = request.form.get('comment')
        if comment_text and comment_text.strip():
            comment = Comment(text=comment_text.strip(), post_id=post.id)
            db.session.add(comment)

        db.session.commit()
        return redirect(url_for('main.post_detail', post_id=post.id))

    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.desc()).all()
    return render_template('post_detail.html', post=post, comments=comments)


@main_bp.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    text = request.form['comment']
    comment = Comment(text=text, post_id=post_id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.post_detail', post_id=post_id))


@main_bp.route('/post/<int:post_id>/vote/<vote>', methods=['POST'])
def vote_post(post_id, vote):
    post = Post.query.get_or_404(post_id)
    if vote == 'up':
        post.votes += 1
    elif vote == 'down':
        post.votes -= 1
    db.session.commit()
    return redirect(url_for('main.post_detail', post_id=post_id))


from flask import request, redirect, url_for, render_template, flash
from flask_login import login_user
from main.models import User, db

@main_bp.route('/main.register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("ім'я користувача або email уже занятий")
            return redirect(url_for('main.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)  

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)  

        return redirect(url_for('main.index'))

    return render_template('register.html')


from flask_login import login_user

@main_bp.route('/main.login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Будьласка, заповніть всі поля', 'error')
            return render_template('login.html', username=username)

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.index'))
        else:
            flash('Неправильній логін або пароль', 'error')
            return render_template('login.html', username=username)

    return render_template('login.html')


from flask_login import logout_user

@main_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main_bp.route('/main.profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(author_id=user.id).all()
    return render_template('profile.html', user=user, posts=posts)


@main_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()

    if form.validate_on_submit():
        current_user.about = form.about.data
        current_user.location = form.location.data
        current_user.discord = form.discord.data
        current_user.email = form.email.data
        current_user.welcome_section = form.welcome.data
        current_user.membership_duration = form.membership_duration.data

        if form.avatar.data:
            filename = secure_filename(form.avatar.data.filename)
            avatar_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(avatar_folder, exist_ok=True)
            file_path = os.path.join(avatar_folder, filename)
            form.avatar.data.save(file_path)
            current_user.avatar_url = f'/{avatar_folder}/{filename}'

        db.session.commit()
        return redirect(url_for('main.profile', user_id=current_user.id))

    elif request.method == 'GET':
        form.about.data = current_user.about
        form.location.data = current_user.location
        form.email.data = current_user.email
        form.welcome.data = current_user.welcome_section
        form.membership_duration.data = current_user.membership_duration

    return render_template('edit_profile.html', form=form)


@main_bp.route('/main.profile/<int:user_id>/activity')
def user_activity(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(author_id=user.id).order_by(Post.created_at.desc()).all()
    comments = Comment.query.filter_by(user_id=user.id).order_by(Comment.created_at.desc()).all()
    return render_template('user_activity.html', user=user, posts=posts, comments=comments)


@main_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id:
        flash('Нет прав удалять этот пост', 'danger')
        return redirect(url_for('main.post_detail', post_id=post.id))
    db.session.delete(post)
    db.session.commit()
    flash('Пост удален', 'success')
    return redirect(url_for('main.profile', user_id=current_user.id))


@main_bp.route('/main.delete_account', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Аккаунт удалён', 'success')
    return redirect(url_for('main.index'))

@main_bp.before_request
def update_last_seen():
    if current_user.is_authenticated:
        now = datetime.utcnow()
        last_seen = current_user.last_seen or datetime(2000, 1, 1)
        if now - last_seen > timedelta(minutes=1):
            current_user.last_seen = now
            current_user.is_online = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()


@main_bp.route('/main.tags')
def tags():
    tags_with_counts = db.session.query(
        Tag,                         
        func.count(Post.id).label('count') 
    ).select_from(post_tags) \
     .join(Tag, post_tags.c.tag_id == Tag.id) \
     .join(Post, post_tags.c.post_id == Post.id) \
     .group_by(Tag.id) \
     .all()

    return render_template('tags.html', tags=tags_with_counts, min=min)


@main_bp.route('/tags/<int:tag_id>')
def tag_detail(tag_id):
    tag = Tag.query.get(tag_id)
    if not tag:
        abort(404)
    questions = tag.posts 
    return render_template('tag_detail.html', tag=tag, questions=questions)


@main_bp.route('/unanswered')
def unanswered():
    posts = Post.query.filter(~Post.comments.any()).order_by(Post.created_at.desc()).all()
    return render_template('unanswered.html', posts=posts)