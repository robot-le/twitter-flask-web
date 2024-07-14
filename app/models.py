from app.search import add_to_index, remove_from_index, query_index
import jwt
from time import time
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, login
from flask import current_app
from flask_login import UserMixin
from hashlib import md5


@login.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
)


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(
        sa.String(64),
        index=True,
        unique=True,
    )
    email: so.Mapped[str] = so.mapped_column(
        sa.String(120),
        index=True,
        unique=True,
    )
    password_hash: so.Mapped[str | None] = so.mapped_column(sa.String(256))
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    about_me: so.Mapped[str | None] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[str | None] = so.mapped_column(
        sa.String(256),
        default=lambda: datetime.now(timezone.utc),
    )
    following: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates='followers',
    )
    followers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates='following',
    )

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def followers_count(self):
        query = (sa.select(sa.func.count())
                 .select_from(self.followers.select().subquery()))
        return db.session.scalar(query)

    def following_count(self):
        query = (sa.select(sa.func.count())
                 .select_from(self.following.select().subquery()))
        return db.session.scalar(query)

    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Author.id == self.id,
                Follower.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    def get_reset_password_token(self, expires_in=600):
        jwt_token = jwt.encode(
            {
                'reset_password': self.id,
                'exp': time() + expires_in,
            },
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256',
        )
        return jwt_token

    @staticmethod
    def verify_reset_password_token(jwt_token):
        try:
            user_id = jwt.decode(
                jwt_token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256'],
            )['reset_password']
        except:
            return

        return db.session.get(User, user_id)


class SearchableMixin:
    @classmethod
    def search(cls, expression, page, per_page) -> sa.engine.result.ScalarResult:
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            # todo: warning
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = (
            sa.select(cls)
            .where(cls.id.in_(ids))
            .order_by(db.case(*when, value=cls.id))
        )
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    user_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey(User.id),
        index=True,
    )
    author: so.Mapped[User] = so.relationship(back_populates='posts')
    language: so.Mapped[str | None] = so.mapped_column(sa.String(5))

    def __repr__(self):
        return '<Post {}>'.format(self.body)
