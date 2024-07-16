import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db, create_app
from app.models import User, Post, Message, Notification, Task

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'sa': sa,
        'so': so,
        'db': db,
        'User': User,
        'Post': Post,
        'Task': Task,
        'Message': Message,
        'Notification': Notification,
    }


if __name__ == '__main__':
    app.run()
