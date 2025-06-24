from datetime import datetime, timedelta
import random
import os
from flask import Blueprint, abort, app, current_app, json, jsonify, render_template, request, redirect, url_for, session
from sqlalchemy import func
from main.forms import EditCommentForm, EditProfileForm
from main.models import CommentVote, Post, Comment, Question, db, User, post_tags, PostVote
import traceback
from flask import flash
#from main.models import check_password_hash
#from main.models import generate_password_hash
from flask import session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from main.models import Tag
from flask import g
from rapidfuzz import fuzz




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
    elif period == 'year':
        date_from = now - timedelta(days=365)
        posts = Post.query.filter(Post.created_at >= date_from).order_by(Post.created_at.desc()).all()
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()

    # Підрахунок голосів і коментарів
    for post in posts:
        post.likes_count = PostVote.query.filter_by(post_id=post.id, value=1).count()
        post.dislikes_count = PostVote.query.filter_by(post_id=post.id, value=-1).count()
        post.comments_count = Comment.query.filter_by(post_id=post.id).count()

    # Додаємо логіку для популярних тегів
    popular_tags = ['javascript', 'python', 'php', 'java', 'c#', 'html', 'c++', 'android', 'css', 'jquery']
    tag_ids = {tag.name.lower(): tag.id for tag in Tag.query.filter(Tag.name.in_(popular_tags)).all()}

    return render_template(
        'index.html',
        posts=posts,
        current_filter=period,
        tag_ids=tag_ids,
        empty_message="Постів за вказаний період не знайдено." if not posts else None
    )


@main_bp.route('/main.posts')
def posts():
    posts = Post.query.all()

    # Подсчёт лайков и дизлайков и комментариев для каждого поста
    for post in posts:
        post.likes_count = PostVote.query.filter_by(post_id=post.id, value=1).count()
        post.dislikes_count = PostVote.query.filter_by(post_id=post.id, value=-1).count()
        post.comments_count = Comment.query.filter_by(post_id=post.id).count()

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

        # 🔽 Завантаження описів тегів із JSON-файлу
        try:
            with open('tag_descriptions.json', encoding='utf-8') as f:
                TAG_DESCRIPTIONS = json.load(f)
        except FileNotFoundError:
            TAG_DESCRIPTIONS = {}

        tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
        tag_objects = []

        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                description = TAG_DESCRIPTIONS.get(name.lower(), '')  # Автоматичне описання
                tag = Tag(name=name, description=description)
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
            db.session.add(post)
            db.session.commit()
            flash('Питання успішно опубліковано!', 'success')
            return redirect('/')
        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            return f'Помилка при додані питання: {e}'

    return render_template('create.html')

@main_bp.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    post.views = (post.views or 0) + 1
    db.session.commit()

    likes = PostVote.query.filter_by(post_id=post.id, value=1).count()
    dislikes = PostVote.query.filter_by(post_id=post.id, value=-1).count()

    user_vote = 0
    if current_user.is_authenticated:
        vote = PostVote.query.filter_by(post_id=post.id, user_id=current_user.id).first()
        if vote:
            user_vote = vote.value

    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.created_at.desc()).all()

    return render_template('post_detail.html', post=post, comments=comments, likes=likes, dislikes=dislikes, user_vote=user_vote)


@main_bp.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        flash('Коментар не може бути пустим', 'warning')
        return redirect(url_for('main.post_detail', post_id=post_id))

    comment = Comment(text=comment_text, post_id=post_id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.post_detail', post_id=post_id))


@main_bp.route('/comment/<int:comment_id>/vote', methods=['POST'])
@login_required
def vote_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    value = request.form.get('vote')  # 'like' или 'dislike'

    if value not in ['like', 'dislike']:
        flash('Невірне значення голосу', 'danger')
        return redirect(url_for('main.post_detail', post_id=comment.post_id))

    vote_value = 1 if value == 'like' else -1

    existing_vote = CommentVote.query.filter_by(comment_id=comment.id, user_id=current_user.id).first()

    if existing_vote:
        if existing_vote.value == vote_value:
            db.session.delete(existing_vote)  # отмена голоса
        else:
            existing_vote.value = vote_value  # смена голоса
    else:
        new_vote = CommentVote(comment_id=comment.id, user_id=current_user.id, value=vote_value)
        db.session.add(new_vote)

    db.session.commit()
    return redirect(url_for('main.post_detail', post_id=comment.post_id))



@main_bp.route('/post/<int:post_id>/vote', methods=['POST'])
@login_required
def vote_post(post_id):
    post = Post.query.get_or_404(post_id)
    value = request.form.get('vote')  # 'like' или 'dislike'

    if value not in ['like', 'dislike']:
        flash('Невірне значення голосу', 'danger')
        return redirect(url_for('main.post_detail', post_id=post.id))

    vote_value = 1 if value == 'like' else -1

    # Ищем, голосовал ли пользователь раньше
    existing_vote = PostVote.query.filter_by(post_id=post.id, user_id=current_user.id).first()

    if existing_vote:
        if existing_vote.value == vote_value:
            db.session.delete(existing_vote)  # отмена голоса
        else:
            existing_vote.value = vote_value  # смена голоса
    else:
        new_vote = PostVote(post_id=post.id, user_id=current_user.id, value=vote_value)
        db.session.add(new_vote)

    db.session.commit()
    return redirect(url_for('main.post_detail', post_id=post.id))


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
        # обновляем поля пользователя из формы
        current_user.about = form.about.data
        current_user.location = form.location.data
        current_user.email = form.email.data
        current_user.welcome_section = form.welcome.data
        current_user.membership_duration = form.membership_duration.data
        
        # Здесь обновляем язык интерфейса пользователя
        current_user.preferred_lang = form.preferred_lang.data or 'uk'

        # Обработка загрузки аватарки (если есть)
        if form.avatar.data:
            filename = secure_filename(form.avatar.data.filename)
            avatar_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(avatar_folder, exist_ok=True)
            file_path = os.path.join(avatar_folder, filename)
            form.avatar.data.save(file_path)
            current_user.avatar_url = f'uploads/avatars/{filename}'

        db.session.commit()
        return redirect(url_for('main.profile', user_id=current_user.id))

    elif request.method == 'GET':
        # Заполняем форму текущими данными пользователя
        form.about.data = current_user.about
        form.location.data = current_user.location
        form.email.data = current_user.email
        form.welcome.data = current_user.welcome_section
        form.membership_duration.data = current_user.membership_duration
        form.preferred_lang.data = current_user.preferred_lang or 'uk'

    return render_template('edit_profile.html', form=form)


@main_bp.route('/main.profile/<int:user_id>/activity')
def user_activity(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(author_id=user.id).order_by(Post.created_at.desc()).all()
    comments = Comment.query.filter_by(user_id=user.id).order_by(Comment.created_at.desc()).all()
    return render_template('user_activity.html', user=user, posts=posts, comments=comments)



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
    tag = Tag.query.get_or_404(tag_id)
    posts = tag.posts

    # Підтягнути опис, якщо відсутній у базі
    if not tag.description:
        with open('tag_descriptions.json', encoding='utf-8') as f:
            tag_descriptions = json.load(f)
        tag.description = tag_descriptions.get(tag.name.lower())

    return render_template('tag_detail.html', tag=tag, posts=posts)


@main_bp.route('/main.unanswered')
def unanswered():
    posts = Post.query.filter(~Post.comments.any()).order_by(Post.created_at.desc()).all()
    return render_template('unanswered.html', posts=posts)

@main_bp.route('/main.ask')
def ask():
    return render_template('ask.html')


@main_bp.route('/main.search_similar', methods=['POST'])
def search_similar():
    data = request.get_json()
    query = data.get('query', '').strip().lower()

    if not query:
        return jsonify([])

    all_questions = Question.query.all()
    results = []

    for q in all_questions:
        similarity = fuzz.token_sort_ratio(query, q.title.lower())
        if similarity >= 60:
            results.append((similarity, q))

    results.sort(reverse=True, key=lambda x: x[0])
    top_matches = results[:5]

    return jsonify([
        {'id': q.id, 'title': q.title}
        for sim, q in top_matches
    ])


@main_bp.route('/users')
def users():
    users = User.query.order_by(User.username.asc()).all()
    return render_template('users_list.html', users=users)


@main_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_admin:
        abort(403)  # Доступ заборонений
    
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']
        post.title = title
        post.text = text
        try:
            db.session.commit()
            flash('Пост успішно оновлено!', 'success')
            return redirect(url_for('main.post_detail', post_id=post.id))
        except Exception as e:
            db.session.rollback()
            flash('Помилка при оновленні поста.', 'danger')

    return render_template('edit_post.html', post=post)

# Видалення поста
@main_bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_admin:
        abort(403)
    try:
        db.session.delete(post)
        db.session.commit()
        flash('Пост видалено!', 'success')
    except Exception:
        db.session.rollback()
        flash('Помилка при видаленні поста.', 'danger')
    return redirect(url_for('main.index'))

# Редагування коментаря
@main_bp.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    # Проверяем, что текущий пользователь — автор комментария
    if comment.user_id != current_user.id:
        flash('У вас немає прав редагувати цей коментар.', 'danger')
        return redirect(url_for('main.post_detail', post_id=comment.post_id))

    form = EditCommentForm()

    if form.validate_on_submit():
        comment.text = form.text.data
        db.session.commit()
        flash('Коментар успішно оновлено.', 'success')
        return redirect(url_for('main.user_activity', user_id=current_user.id))

    elif request.method == 'GET':
        form.text.data = comment.text

    return render_template('edit_comment.html', form=form, comment=comment)

# Видалення коментаря
@main_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if comment.user != current_user and not current_user.is_admin:
        abort(403)
    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Коментар видалено!', 'success')
    except Exception:
        db.session.rollback()
        flash('Помилка при видаленні коментаря.', 'danger')
    return redirect(url_for('main.post_detail', post_id=comment.post_id))


@main_bp.route('/set_lang/<lang>')
@login_required  # если хочешь, чтобы язык менял только авторизованный
def set_lang(lang):
    if lang not in ['uk', 'en']:
        lang = 'uk'
    session['lang'] = lang
    # Возврат на предыдущую страницу или на главную
    next_page = request.referrer or url_for('main.index')
    return redirect(next_page)