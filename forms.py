from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, FieldList, FormField, SelectField, TextAreaField # <--- Añadir TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms import IntegerField, SelectField
from wtforms import DateField

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

class ExerciseForm(FlaskForm):
    name = StringField('Nombre del Ejercicio', validators=[DataRequired()])
    muscle_group = SelectField('Grupo Muscular', choices=[
        ('Pecho', 'Pecho'), ('Espalda', 'Espalda'), 
        ('Pierna', 'Pierna'), ('Hombro', 'Hombro'), 
        ('Bíceps', 'Bíceps'), ('Tríceps', 'Tríceps'), 
        ('Abdominales', 'Abdominales'), ('Cardio', 'Cardio'), ('Otro', 'Otro')
    ])
    burn_rate = FloatField('Quema Estimada (Kcal/min o Kcal/rep)', validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField('Descripción / Notas Técnicas')
    video_link = StringField('Link Video (Youtube)')
    submit = SubmitField('Guardar Ejercicio')

class RoutineForm(FlaskForm):
    name = StringField('Nombre de la Rutina', validators=[DataRequired()])
    description = StringField('Descripción')
    submit = SubmitField('Guardar Rutina')

class BodyMeasurementForm(FlaskForm):
    # Añadimos Optional() en todos los campos para que WTForms ignore los vacíos
    date = DateField('Fecha', format='%Y-%m-%d', validators=[Optional()])
    weight = FloatField('Peso (kg)', validators=[Optional(), NumberRange(min=0)])
    biceps = FloatField('Bíceps (cm)', validators=[Optional(), NumberRange(min=0)])
    chest = FloatField('Pecho (cm)', validators=[Optional(), NumberRange(min=0)])
    hips = FloatField('Cadera (cm)', validators=[Optional(), NumberRange(min=0)])
    thigh = FloatField('Muslo (cm)', validators=[Optional(), NumberRange(min=0)])
    calf = FloatField('Gemelo (cm)', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Registrar')

class UserAdminForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña (dejar en blanco para mantener la actual)', validators=[Optional(), Length(min=6)])
    
    # Perfil Físico
    age = IntegerField('Edad', validators=[Optional(), NumberRange(min=0)])
    height = FloatField('Altura (cm)', validators=[Optional(), NumberRange(min=0)])
    weight = FloatField('Peso Actual (kg)', validators=[Optional(), NumberRange(min=0)])
    gender = SelectField('Género', choices=[('Male', 'Hombre'), ('Female', 'Mujer')], validators=[Optional()])
    target_weight = FloatField('Objetivo de Peso (kg)', validators=[Optional(), NumberRange(min=0)])
    
    is_admin = BooleanField('Es Administrador')
    submit = SubmitField('Guardar Usuario')