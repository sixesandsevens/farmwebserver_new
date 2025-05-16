# forms.py
from flask_wtf import FlaskForm
from wtforms     import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length


from models import User

class RegistrationForm(FlaskForm):
    username         = StringField('Username', validators=[DataRequired()])
    email            = StringField('Email',    validators=[DataRequired(), Email()])
    referrer         = StringField('Referred by', validators=[Length(max=120)])
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
    old_password = PasswordField(
        'Old Password',
        validators=[DataRequired()]
    )
    new_password = PasswordField(
        'New Password',
        validators=[DataRequired()]
    )
    confirm = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(),
            EqualTo(
                'new_password',
                message="Passwords must match"
            )
        ]
    )
    submit = SubmitField('Update Password')


class FeedbackForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField('Send Feedback')