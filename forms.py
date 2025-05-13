# forms.py
from flask_wtf import FlaskForm
from wtforms     import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from models import User

class RegistrationForm(FlaskForm):
    username         = StringField('Username', validators=[DataRequired()])
    email            = StringField('Email',    validators=[DataRequired(), Email()])
    password         = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit           = SubmitField('Register')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Username already exists.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email    = StringField('Email',    validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')

class PasswordChangeForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm      = PasswordField('Confirm New Password',
                                 validators=[DataRequired(), EqualTo('new_password',
                                       message="Passwords must match")])
    submit       = SubmitField('Update Password')
