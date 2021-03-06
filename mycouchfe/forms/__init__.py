from datetime import datetime, date
from flask.ext.wtf import (
    Form, PasswordField, TextField, TextAreaField, DateTimeField, SelectField,
    IntegerField, DateField,
    ValidationError, Length, Required, Email, EqualTo)


def serialize_datetime(dt_val):
    return dt_val.strftime('%Y-%m-%dT%H:%M:%S')


# Validators

class PastDateTime(object):
    def __init__(self):
        pass

    def __call__(self, form, field):
        val = field.data
        if isinstance(val, datetime):
            now = datetime.now()
        elif isinstance(val, date):
            now = date.today()
        else:
            raise ValidationError('Value is not a valid date/datetime object')
        if val and not (val < now):
            raise ValidationError('Date/datetime not in the past.')


class FutureDateTime(object):
    def __init__(self):
        pass

    def __call__(self, form, field):
        val = field.data
        if isinstance(val, datetime):
            now = datetime.now()
        elif isinstance(val, date):
            now = date.today()
        else:
            raise ValidationError('Value is not a valid date/datetime object')
        if val and (val < now):
            raise ValidationError('Date/datetime not in the past.')


class GreaterThan(object):
    fieldname = None

    def __init__(self, fieldname):
        self.fieldname = fieldname

    def __call__(self, form, field):
        val1 = getattr(form, self.fieldname, None).data
        val2 = field.data
        if val1 is None or val2 <= val1:
            raise ValidationError('This value must be greater than `%s`.' %
                self.fieldname)

# Forms

class LoginForm(Form):
    force_error = False
    username = TextField('Username', description='The username.',
                         validators=[Required()])
    password = PasswordField('Password', description='The password.',
                             validators=[Required()])

    def validate(self):
        return super(LoginForm, self).validate() or self.force_error


class NewUserForm(Form):
    username = TextField('Username', description='The username.',
                         validators=[Required()])
    password = PasswordField('Password', description='The password.',
                             validators=[Required()])
    confirm_password = PasswordField('Confirm password', description='The password (again).',
                                     validators=[Required(), EqualTo('password')])
    first_name = TextField('First name', description='The first name.',
                           validators=[Required()])
    last_name = TextField('Last name', description='The last name.',
                          validators=[Required()])
    email = TextField('E-mail', description='The e-mail address.',
                       validators=[Required(), Email()])
    birth_date = DateField('Date of birth', description='The date of birth.',
                           validators=[Required(), PastDateTime()])
    gender = SelectField('Gender', description='The gender.',
                         validators=[Required()],
                         choices=[
                            ('1', 'Female'),
                            ('2', 'Male'),
                         ], coerce=str)
    city_id = IntegerField('City ID', description='The city.',
                           validators=[Required()])
    def as_dict(self):
        return {
            'username': self.username.data,
            'password': self.password.data,
            'first_name': self.first_name.data,
            'last_name': self.last_name.data,
            'email': self.email.data,
            'birth_date': self.birth_date.data,
            'gender': self.gender.data,
            'city_id': self.city_id.data,
        }


class NewActivityForm(Form):
    force_error = False
    title = TextField('Title', description='The title.',
                      validators=[Required()])
    description = TextAreaField('Description', description='The description.',
                                validators=[Required()])
    scheduled_from = DateTimeField('From', description='Date/time from.',
                                   format='%Y-%m-%d %H:%M',
                                   validators=[Required(), FutureDateTime()])
    scheduled_until = DateTimeField('Until', description='Date/time until.',
                                    format='%Y-%m-%d %H:%M',
                                    validators=[Required(), FutureDateTime(),
                                                GreaterThan('scheduled_from')])
    location = TextField('Location', description='The location.',
                         validators=[Required(), Length(max=64)])
    locality_id = SelectField('Locality', description='The locality.',
                              validators=[Required()])

    def get_request_data(self):
        return {
            'title': self.title.data,
            'description': self.description.data,
            'scheduled_from': serialize_datetime(self.scheduled_from.data),
            'scheduled_until': serialize_datetime(self.scheduled_until.data),
            'location': self.location.data,
            'locality_id': long(self.locality_id.data),
        }
