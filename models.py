from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# --- USUARIO ---
class User(UserMixin, db.Model):
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

# --- RECETAS ---
class Receta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    kcal = db.Column(db.Integer, default=0)
    tipo = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    ingredientes = db.relationship('Ingrediente', backref='receta', lazy=True, cascade="all, delete-orphan")

class Ingrediente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    unidad = db.Column(db.String(20), nullable=False)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'), nullable=False)

# --- MENU SEMANAL (REWORK MULTI-SELECCIÓN) ---
class MenuSemanal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dia = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relación con las selecciones múltiples
    selecciones = db.relationship('MenuSelection', backref='menu_dia', lazy='dynamic', cascade="all, delete-orphan")

    def get_recetas(self, tipo):
        """Devuelve una lista de recetas para un tipo de comida específico (ej: 'Cena')"""
        selections = self.selecciones.filter_by(tipo_comida=tipo).all()
        return [s.receta for s in selections]

class MenuSelection(db.Model):
    """Tabla intermedia para permitir múltiples recetas por comida"""
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_semanal.id'), nullable=False)
    receta_id = db.Column(db.Integer, db.ForeignKey('receta.id'), nullable=False)
    tipo_comida = db.Column(db.String(20)) # 'Desayuno', 'Comida', etc.
    
    receta = db.relationship('Receta')

# --- HOGAR ---
class TareaLimpieza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    asignado_a = db.Column(db.String(50))
    frecuencia = db.Column(db.String(50))
    ultimo_realizado = db.Column(db.Date)
    proxima_fecha = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Lavadora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50))
    dia_preferente = db.Column(db.String(20))
    estado = db.Column(db.String(20), default="Pendiente")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ShoppingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Float, default=1.0)
    unidad = db.Column(db.String(20), default="ud")
    completed = db.Column(db.Boolean, default=False)
    is_auto = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)