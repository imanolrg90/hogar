from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# --- USUARIO ---
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Datos Físicos
    age = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Float, nullable=True) 
    weight = db.Column(db.Float, nullable=True) 
    gender = db.Column(db.String(10), nullable=True)
    target_weight = db.Column(db.Float, nullable=True) 
    basal_metabolism = db.Column(db.Float, nullable=True)

    # RELACIONES EXISTENTES
    recetas = db.relationship('Receta', backref='user', lazy=True)
    menus = db.relationship('MenuSemanal', backref='user', lazy=True)
    tareas = db.relationship('TareaLimpieza', backref='user', lazy=True)
    lavadoras = db.relationship('Lavadora', backref='user', lazy=True)
    items_compra = db.relationship('ShoppingItem', backref='user', lazy=True)
    measurements = db.relationship('BodyMeasurement', backref='user', lazy=True)
    
    # --- NUEVAS RELACIONES (Solucionan tu error) ---
    # Esto permite usar r.user.username en rutinas y ex.user.username en ejercicios
    exercises = db.relationship('Exercise', backref='user', lazy=True)
    routines = db.relationship('Routine', backref='user', lazy=True)
    # -----------------------------------------------

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def calculate_bmr(self):
        if self.weight and self.height and self.age and self.gender:
            base = (10 * self.weight) + (6.25 * self.height) - (5 * self.age)
            if self.gender == 'Male':
                self.basal_metabolism = base + 5
            else:
                self.basal_metabolism = base - 161
        else:
            self.basal_metabolism = 0

# --- INGREDIENTES ---
class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    kcal_100g = db.Column(db.Float, nullable=False)
    price_kg = db.Column(db.Float, nullable=False)
    
    recipes_assoc = db.relationship("RecipeIngredient", back_populates="ingredient", cascade="all, delete-orphan")

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredients'
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), primary_key=True)
    quantity_g = db.Column(db.Float, nullable=False)

    ingredient = db.relationship("Ingredient", back_populates="recipes_assoc")
    recipe = db.relationship("Receta", back_populates="ingredients_assoc")

# --- RECETAS ---
class Receta(db.Model):
    __tablename__ = 'recipe'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text)
    kcal = db.Column(db.Float, default=0)
    precio = db.Column(db.Float, default=0.0)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ingredients_assoc = db.relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

    @property
    def total_stats(self):
        try:
            k = sum([(i.quantity_g / 100) * i.ingredient.kcal_100g for i in self.ingredients_assoc])
            p = sum([(i.quantity_g / 1000) * i.ingredient.price_kg for i in self.ingredients_assoc])
            return {'kcal': round(k), 'price': round(p, 2)}
        except:
            return {'kcal': 0, 'price': 0}

# --- MENU SEMANAL ---
class MenuSemanal(db.Model):
    __tablename__ = 'menu_semanal'
    id = db.Column(db.Integer, primary_key=True)
    dia = db.Column(db.String(20))
    week_start = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    selecciones = db.relationship('MenuSelection', backref='menu_dia', lazy='dynamic', cascade="all, delete-orphan")

    def get_selections(self, tipo):
        if self.id is None: return []
        return self.selecciones.filter_by(tipo_comida=tipo).all()

    @property
    def daily_stats(self):
        total_k = 0
        total_p = 0
        for s in self.selecciones:
            if s.receta:
                stats = s.receta.total_stats
                total_k += stats['kcal']
                total_p += stats['price']
            elif s.ingredient:
                total_k += (s.quantity / 100) * s.ingredient.kcal_100g
                total_p += (s.quantity / 1000) * s.ingredient.price_kg
        return {'kcal': round(total_k), 'price': round(total_p, 2)}

class MenuSelection(db.Model):
    __tablename__ = 'menu_selection'
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_semanal.id'), nullable=False)
    tipo_comida = db.Column(db.String(20))
    receta_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    receta = db.relationship('Receta')
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=True)
    ingredient = db.relationship('Ingredient')
    quantity = db.Column(db.Float, default=0.0)

# --- OTROS ---
class TareaLimpieza(db.Model):
    __tablename__ = 'tarea_limpieza'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    asignado_a = db.Column(db.String(50))
    frecuencia = db.Column(db.String(50))
    ultimo_realizado = db.Column(db.Date)
    proxima_fecha = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Lavadora(db.Model):
    __tablename__ = 'lavadora'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))
    dia_preferente = db.Column(db.String(20))
    estado = db.Column(db.String(20), default="Pendiente")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ShoppingItem(db.Model):
    __tablename__ = 'shopping_item'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Float, default=1.0)
    unidad = db.Column(db.String(20), default="ud")
    completed = db.Column(db.Boolean, default=False)
    is_auto = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# --- GYM ---
class Exercise(db.Model):
    __tablename__ = 'exercise'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    muscle_group = db.Column(db.String(50)) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sets = db.relationship('WorkoutSet', backref='exercise', lazy=True)
    description = db.Column(db.Text, nullable=True)
    video_link = db.Column(db.String(255), nullable=True)
    
    # --- NUEVO CAMPO ---
    # Para Cardio: Kcal/minuto | Para Fuerza: Kcal/repetición
    burn_rate = db.Column(db.Float, default=0.0) 
    # -------------------

    @property
    def is_cardio(self):
        return self.muscle_group == 'Cardio'

class WorkoutSession(db.Model):
    __tablename__ = 'workout_session'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo_filename = db.Column(db.String(255), nullable=True)
    sets = db.relationship('WorkoutSet', backref='session', cascade="all, delete-orphan", lazy=True)

    @property
    def summary(self):
        exercises = set([s.exercise.name for s in self.sets])
        return ", ".join(exercises)
    @property
    def total_calories(self):
        total = 0
        for s in self.sets:
            total += s.est_calories
        return round(total)

class WorkoutSet(db.Model):
    __tablename__ = 'workout_set'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    weight = db.Column(db.Float, default=0)
    reps = db.Column(db.Integer, default=0)
    distance = db.Column(db.Float, default=0.0)
    time = db.Column(db.Integer, default=0)
    order = db.Column(db.Integer, default=1)
    @property
    def est_calories(self):
        rate = self.exercise.burn_rate or 0
        if self.exercise.is_cardio:
            # Cardio: Tasa * Minutos
            return rate * (self.time or 0)
        else:
            # Fuerza: Tasa * Repeticiones
            return rate * (self.reps or 0)

class Routine(db.Model):
    __tablename__ = 'routine'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercises = db.relationship('RoutineExercise', backref='routine', cascade="all, delete-orphan", lazy=True)

class RoutineExercise(db.Model):
    __tablename__ = 'routine_exercise'
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    order = db.Column(db.Integer, default=1)
    series = db.Column(db.Integer, default=3)
    rest_seconds = db.Column(db.Integer, default=90)
    target_distance = db.Column(db.Float, default=0.0)
    target_time = db.Column(db.Integer, default=0)
    
    exercise = db.relationship('Exercise')

class BodyMeasurement(db.Model):
    __tablename__ = 'body_measurement'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    weight = db.Column(db.Float)
    biceps = db.Column(db.Float)
    chest = db.Column(db.Float)
    hips = db.Column(db.Float)
    thigh = db.Column(db.Float)
    calf = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)