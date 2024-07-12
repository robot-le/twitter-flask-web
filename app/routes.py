from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    g,
)
from flask_login import (
    current_user,
    login_required,
)
import sqlalchemy as sa
from app import app, db, detector, translator
from app.forms import (
    EditProfileForm,
    EmptyForm,
    PostForm,
)
from app.models import User, Post
from datetime import datetime, timezone
from flask_babel import _, get_locale

current_user: User


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        lang = detector.detect_language_of(form.post.data)
        post = Post(
            body=form.post.data,
            author=current_user,
            language=lang.iso_code_639_1.name.lower(),
        )
        db.session.add(post)
        db.session.commit()
        flash(_('Your post in now live!'))
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        current_user.following_posts(),
        page=page,
        per_page=app.config.get('POSTS_PER_PAGE'),
        error_out=False,
    )

    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Home Page',
        posts=posts.items,
        form=form,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(
        query,
        page=page,
        per_page=app.config.get('POSTS_PER_PAGE'),
        error_out=False,
    )

    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Explore',
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route('/user/<username>')
@login_required
def user(username):
    user_obj = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user_obj.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for(
        'user', username=user_obj.username, page=posts.next_num
    ) if posts.has_next else None
    prev_url = url_for(
        'user', username=user_obj.username, page=posts.prev_num
    ) if posts.has_prev else None
    form = EmptyForm()
    return render_template(
        'user.html',
        user=user_obj,
        posts=posts.items,
        form=form,
        next_url=next_url,
        prev_url=prev_url,
    )


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.email = form.email.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.email.data = current_user.email
    return render_template(
        'edit_profile.html',
        title='Edit Profile',
        form=form,
    )


@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    form = EmptyForm()

    if form.validate_on_submit():
        user_obj = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user_obj is None:
            flash(_(f'User %(username) not found.', username=username))
            return redirect(url_for('index'))
        if user_obj == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('user', username=username))
        current_user.follow(user_obj)
        db.session.commit()
        flash(_(f'You are following %(username)!', username=username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user_obj = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user_obj is None:
            flash(_(f'User %(username) not found.', username=username))
            return redirect(url_for('index'))
        if user_obj == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('user', username=username))
        current_user.unfollow(user_obj)
        db.session.commit()
        flash(_(f'You are not following %(username).', username=username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    result = translator.translate(
        data.get('text'),
        source_language=data.get('source_language'),
        target_language=data.get('dest_language'),
    )
    return {'text': result.get('translatedText')}
