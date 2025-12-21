from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, FieldList, FormField, SelectField
from wtforms.validators import DataRequired, NumberRange
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class IngredienteForm(FlaskForm):
    nombre = StringField('Nombre del Ingrediente', validators=[DataRequired()])
    cantidad = FloatField('Cantidad', validators=[DataRequired(), NumberRange(min=0)])
    unidad = StringField('Unidad', validators=[DataRequired()])

class RecetaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    kcal = FloatField('Kcal', validators=[NumberRange(min=0)])
    precio = FloatField('Precio (€)', validators=[NumberRange(min=0)]) # <--- NUEVO
    tipo = SelectField('Tipo', choices=[
        ('Desayuno', 'Desayuno'), 
        ('Comida', 'Comida'), 
        ('Merienda', 'Merienda'), 
        ('Cena', 'Cena'), 
        ('Ambos', 'Comida/Cena (Ambos)')
    ])
    ingredientes = FieldList(FormField(IngredienteForm), min_entries=1)
    submit = SubmitField('Guardar')

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Repetir Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')