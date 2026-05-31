
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Generation(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    content_image = db.Column(
        db.String(300)
    )

    style_image = db.Column(
        db.String(300)
    )

    output_image = db.Column(
        db.String(300)
    )

    alpha = db.Column(
        db.Float,
        default=1.0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
