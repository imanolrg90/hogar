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
    
    recetas = db.relationship('Receta', backref='user', lazy=True)
    menus = db.relationship('MenuSemanal', backref='user', lazy=True)
    tareas = db.relationship('TareaLimpieza', backref='user', lazy=True)
    lavadoras = db.relationship('Lavadora', backref='user', lazy=True)
    items_compra = db.relationship('ShoppingItem', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- INGREDIENTES (Modelo Correcto: Ingredient) ---
class Ingredient(db.Model):
    __tablename__ = 'ingredient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    kcal_100g = db.Column(db.Float, nullable=False)
    price_kg = db.Column(db.Float, nullable=False)
    
    # Relación inversa
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
    title = db.Column(db.String(100), nullable=False) # Usamos 'title' para estandarizar
    description = db.Column(db.Text)
    steps = db.Column(db.Text)
    # Estos campos son caché (opcionales si calculas dinámicamente)
    kcal = db.Column(db.Float, default=0)
    precio = db.Column(db.Float, default=0.0)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relación con ingredientes (Tabla intermedia)
    ingredients_assoc = db.relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")

    @property
    def total_stats(self):
        """Calcula totales dinámicamente basándose en los ingredientes"""
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
    dia = db.Column(db.String(20)) # "Lunes", "Martes"...
    week_start = db.Column(db.Date, nullable=True) # <--- NUEVO CAMPO
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    selecciones = db.relationship('MenuSelection', backref='menu_dia', lazy='dynamic', cascade="all, delete-orphan")

    def get_selections(self, tipo):
        """Devuelve todas las selecciones (recetas o ingredientes) de un tipo de comida"""
        # --- FIX: Si es un objeto dummy (sin ID), no consultamos la BD ---
        if self.id is None:
            return []
        # -----------------------------------------------------------------
        return self.selecciones.filter_by(tipo_comida=tipo).all()

    @property
    def daily_stats(self):
        total_k = 0
        total_p = 0
        for s in self.selecciones:
            # Caso 1: Es una Receta
            if s.receta:
                stats = s.receta.total_stats
                total_k += stats['kcal']
                total_p += stats['price']
            
            # Caso 2: Es un Ingrediente suelto
            elif s.ingredient:
                # Kcal: (gramos / 100) * kcal_100g
                total_k += (s.quantity / 100) * s.ingredient.kcal_100g
                # Precio: (gramos / 1000) * price_kg
                total_p += (s.quantity / 1000) * s.ingredient.price_kg
                
        return {'kcal': round(total_k), 'price': round(total_p, 2)}

# Actualiza MenuSelection
class MenuSelection(db.Model):
    __tablename__ = 'menu_selection'
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_semanal.id'), nullable=False)
    tipo_comida = db.Column(db.String(20))
    
    # Puede ser receta...
    receta_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    receta = db.relationship('Receta')
    
    # ... O puede ser ingrediente suelto
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=True)
    ingredient = db.relationship('Ingredient')
    quantity = db.Column(db.Float, default=0.0) # Cantidad en gramos para el ingrediente suelto

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

class Exercise(db.Model):
    __tablename__ = 'exercise'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    muscle_group = db.Column(db.String(50)) # Pecho, Espalda, Pierna...
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relación para ver el historial
    sets = db.relationship('WorkoutSet', backref='exercise', lazy=True)

class WorkoutSession(db.Model):
    __tablename__ = 'workout_session'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow) # Ojo: asegúrate de importar datetime arriba si no está
    note = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    sets = db.relationship('WorkoutSet', backref='session', cascade="all, delete-orphan", lazy=True)

    @property
    def summary(self):
        """Devuelve un resumen de ejercicios tocados en esta sesión"""
        exercises = set([s.exercise.name for s in self.sets])
        return ", ".join(exercises)

class WorkoutSet(db.Model):
    __tablename__ = 'workout_set'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, default=1) # Para saber qué serie fue primero

    # --- RUTINAS DE GIMNASIO ---
class Routine(db.Model):
    __tablename__ = 'routine'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Ej: "Empuje A", "Pierna Hipertrofia"
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relación con los ejercicios de la rutina
    exercises = db.relationship('RoutineExercise', backref='routine', cascade="all, delete-orphan", lazy=True)

class RoutineExercise(db.Model):
    __tablename__ = 'routine_exercise'
    id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercise.id'), nullable=False)
    order = db.Column(db.Integer, default=1) # Para que salgan en orden
    
    # Podemos acceder al objeto ejercicio completo desde aquí
    exercise = db.relationship('Exercise')

# --- MODIFICACIÓN: Añade esto a WorkoutSession si quieres saber qué rutina usaste ---
# (Si no quieres borrar la tabla antigua, puedes saltarte este campo o usar migraciones, 
# pero para desarrollo local rápido, añade el campo y borra la db antigua si da error)
# class WorkoutSession(...):
#     ... campos existentes ...
#     routine_used_id = db.Column(db.Integer, db.ForeignKey('routine.id'), nullable=True)