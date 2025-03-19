from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Optional, URL

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    resume = FileField('Resume', validators=[
        FileAllowed(['pdf', 'docx', 'doc', 'txt'], 'Only PDF, Word, or text documents are allowed.')
    ])
    csrf_token = StringField('CSRF Token')
    submit = SubmitField('Save Profile')
