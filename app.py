import os
from werkzeug.utils import secure_filename
import re
import json
import datetime
# Importa el nuevo formulario
from forms import UserAdminForm 

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
# En app.py, cambia la línea de importación por esta:
from models import db, User, Receta, MenuSemanal, MenuSelection, TareaLimpieza, Lavadora, ShoppingItem, Ingredient, RecipeIngredient
from forms import RecetaForm, LoginForm, RegistrationForm
from datetime import datetime, timedelta, date # Asegúrate de importar esto
from models import Exercise, WorkoutSession, WorkoutSet # Añadir a la lista existente
from forms import ExerciseForm # Añadir a la lista existente
from models import Routine, RoutineExercise # Añadir a la lista
from forms import RoutineForm # Añadir a la lista
from models import BodyMeasurement # Añadir
from forms import BodyMeasurementForm # Añadir
from sqlalchemy import inspect, text
# --- Configuración Inicial ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_pro_home_os' # Cambia esto en producción
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///home_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
# Inicializar extensiones
db.init_app(app)

# --- Configuración de Login ---
login = LoginManager(app)
login.login_view = 'login' # Redirige aquí si no estás logueado
login.login_message = "Por favor, inicia sesión para acceder a tu hogar."
login.login_message_category = "info"

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Crear tablas al inicio si no existen
with app.app_context():
    db.create_all()

@app.route('/ingredients', methods=['GET', 'POST'])
@login_required
def ingredients_manager():
    if request.method == 'POST':
        name = request.form.get('name')
        try:
            kcal = float(request.form.get('kcal'))
            price_kg = float(request.form.get('price_kg')) # Input directo en KG
        except ValueError:
            flash('Introduce valores numéricos válidos.', 'error')
            return redirect(url_for('ingredients_manager'))
        
        exists = Ingredient.query.filter_by(name=name).first()
        if not exists:
            # Guardamos directamente price_kg
            new_ing = Ingredient(name=name, kcal_100g=kcal, price_kg=price_kg)
            db.session.add(new_ing)
            db.session.commit()
            flash('Ingrediente añadido.', 'success')
        else:
            flash('Ese ingrediente ya existe.', 'warning')
            
        return redirect(url_for('ingredients_manager'))
        
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()
    return render_template('food/ingredients.html', ingredients=all_ingredients)

@app.route('/create_recipe', methods=['GET', 'POST'])
@login_required
def create_recipe():
    """
    Crea una receta vinculando ingredientes existentes y sus cantidades.
    Recibe un JSON desde el frontend con la lista de ingredientes seleccionados.
    """
    # Cargamos ingredientes para el desplegable (select)
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        steps = request.form.get('steps')
        
        # 1. Crear la Receta Base
        new_recipe = Receta(
            title=title, 
            description=description, 
            steps=steps, 
            user_id=current_user.id
        )
        db.session.add(new_recipe)
        db.session.flush() # Importante: Genera el ID de la receta antes de seguir

        # 2. Procesar JSON de ingredientes (viene del JavaScript del Frontend)
        ing_data_json = request.form.get('ingredients_data')
        
        if ing_data_json:
            try:
                items = json.loads(ing_data_json)
                for item in items:
                    # Guardamos en la tabla intermedia (RecipeIngredient)
                    assoc = RecipeIngredient(
                        recipe_id=new_recipe.id,
                        ingredient_id=int(item['id']),
                        quantity_g=float(item['qty'])
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(f"Error procesando ingredientes: {e}")
                flash('Hubo un error al guardar los ingredientes.', 'error')
        
        db.session.commit()
        flash(f'Receta "{title}" creada correctamente.', 'success')
        return redirect(url_for('create_recipe'))

    return render_template('food/create_recipe.html', ingredients=all_ingredients)


# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('dashboard'))
        
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Verificar si ya existe usuario o email
        if User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first():
            flash('El usuario o email ya existe.', 'warning')
            return redirect(url_for('register'))

        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Registro completado! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))
@app.route('/')
@login_required
def dashboard():
    from datetime import date, timedelta, datetime
    
    # 1. Fechas base
    hoy = date.today()
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual_str = dias_semana[hoy.weekday()]
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    
    # Rango de tiempo para "HOY"
    today_start = datetime(hoy.year, hoy.month, hoy.day)
    today_end = today_start + timedelta(days=1)

    # 2. Consultas básicas
    menu_hoy = MenuSemanal.query.filter_by(
        user_id=current_user.id, 
        dia=dia_actual_str,
        week_start=inicio_semana_actual
    ).first()

    workout_hoy = WorkoutSession.query.filter(
        WorkoutSession.user_id == current_user.id,
        WorkoutSession.date >= today_start,
        WorkoutSession.date < today_end
    ).first()

    peso_hoy = BodyMeasurement.query.filter(
        BodyMeasurement.user_id == current_user.id,
        BodyMeasurement.date >= today_start,
        BodyMeasurement.date < today_end
    ).first()

    # 3. CÁLCULO DEL PROGRESO (GRÁFICA HISTÓRICA)
    first_m = BodyMeasurement.query.filter_by(user_id=current_user.id).order_by(BodyMeasurement.date.asc()).first()
    last_m = BodyMeasurement.query.filter_by(user_id=current_user.id).order_by(BodyMeasurement.date.desc()).first()
    
    progress_list = []
    if first_m and last_m:
        metrics = [('weight', 'Peso', 'kg'), ('chest', 'Pecho', 'cm'), ('biceps', 'Bíceps', 'cm'), 
                   ('hips', 'Cadera', 'cm'), ('thigh', 'Muslo', 'cm'), ('calf', 'Gemelo', 'cm')]
        for field, label, unit in metrics:
            val_start = getattr(first_m, field)
            val_end = getattr(last_m, field)
            if val_start is not None and val_end is not None:
                diff = val_end - val_start
                if abs(diff) > 0:
                    progress_list.append({'label': label, 'diff': round(diff, 2), 'unit': unit})

    # 4. CÁLCULO DE DIFERENCIA DIARIA DE PESO (NUEVO)
    weight_diff = None
    if peso_hoy:
        # Buscamos el último registro que sea ANTERIOR a hoy
        peso_ayer = BodyMeasurement.query.filter(
            BodyMeasurement.user_id == current_user.id,
            BodyMeasurement.date < today_start
        ).order_by(BodyMeasurement.date.desc()).first()
        
        if peso_ayer and peso_ayer.weight:
            weight_diff = peso_hoy.weight - peso_ayer.weight

    # 5. CÁLCULO DE BALANCE CALÓRICO
    kcal_ingesta = menu_hoy.daily_stats['kcal'] if menu_hoy else 0
    kcal_quemadas = workout_hoy.total_calories if workout_hoy else 0
    kcal_basal = current_user.basal_metabolism or 0
    
    limite_diario = kcal_basal + kcal_quemadas
    balance = limite_diario - kcal_ingesta

    return render_template('dashboard.html', 
                           menu=menu_hoy, 
                           workout=workout_hoy,
                           peso=peso_hoy,
                           progress=progress_list,
                           kcal_ingesta=kcal_ingesta,
                           kcal_quemadas=kcal_quemadas,
                           kcal_basal=kcal_basal,
                           balance=balance,
                           weight_diff=weight_diff) # <--- Pasamos la nueva variable

@app.route('/recetas')
@login_required
def recetas_page():
    # Mostrar recetas solo del usuario, ordenadas por la más reciente
    recetas = Receta.query.order_by(Receta.id.desc()).all()
    return render_template('food/recetas.html', recetas=recetas)    


@app.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecetaForm()
    
    if request.method == 'POST':
        # Validación manual de campos principales
        nombre = request.form.get('nombre')
        kcal = request.form.get('kcal')
        tipo = request.form.get('tipo')

        if nombre and kcal:
            try:
                # 1. Crear Receta vinculada al usuario
                nueva_receta = Receta(
                    nombre=nombre,
                    kcal=float(kcal),
                    tipo=tipo,
                    user_id=current_user.id # Importante: Asignar al usuario
                )
                db.session.add(nueva_receta)
                db.session.commit() # Commit para obtener ID

                # 2. Procesar Ingredientes (Lógica manual robusta)
                ingredientes_temp = {}
                
                for key, value in request.form.items():
                    # Buscar patrones 'ingredientes-X-campo'
                    match = re.match(r'ingredientes-(\d+)-(\w+)', key)
                    if match:
                        index = match.group(1)
                        field = match.group(2) # nombre, cantidad, unidad
                        
                        if index not in ingredientes_temp:
                            ingredientes_temp[index] = {}
                        
                        ingredientes_temp[index][field] = value

                # Guardar ingredientes
                for index, datos in ingredientes_temp.items():
                    if datos.get('nombre') and datos.get('cantidad'):
                        nuevo_ing = Ingrediente(
                            nombre=datos['nombre'],
                            cantidad=float(datos['cantidad']),
                            unidad=datos.get('unidad', 'ud'),
                            receta_id=nueva_receta.id
                        )
                        db.session.add(nuevo_ing)

                db.session.commit()
                flash(f'Receta "{nombre}" guardada con éxito.', 'success')
                return redirect(url_for('recetas_page'))

            except Exception as e:
                db.session.rollback()
                print(f"Error DB: {e}")
                flash(f'Error al guardar la receta: {e}', 'danger')
        else:
            flash('Nombre y Kcal son obligatorios.', 'warning')

    # Si es GET o fallo, mostrar form. Asegurar al menos una fila de ingrediente.
    if not form.ingredientes.entries:
        form.ingredientes.append_entry()
        
    return render_template('food/add_recipe.html', form=form)

@app.route('/menu', methods=['GET', 'POST'])
@app.route('/menu/<week_str>', methods=['GET', 'POST'])
@login_required
def menu_semanal_page(week_str=None):
    # -----------------------------------------------------------
    # 1. Configuración de Fechas
    # -----------------------------------------------------------
    if week_str:
        try:
            current_week = datetime.strptime(week_str, '%Y-%m-%d').date()
        except ValueError:
            hoy = date.today()
            current_week = hoy - timedelta(days=hoy.weekday())
    else:
        hoy = date.today()
        current_week = hoy - timedelta(days=hoy.weekday())

    # Para el badge de "Semana Actual"
    hoy_real = date.today()
    real_current_week = hoy_real - timedelta(days=hoy_real.weekday())

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    tipos_comida = ['Desayuno', 'Comida', 'Merienda', 'Cena']

    # -----------------------------------------------------------
    # 2. Lógica de Guardado (POST)
    # -----------------------------------------------------------
    if request.method == 'POST':
        try:
            for dia in dias_semana:
                # A. Buscar o Crear el registro del Día (padre)
                menu_dia = MenuSemanal.query.filter_by(
                    user_id=current_user.id,
                    week_start=current_week,  # <--- CORREGIDO: Objeto date puro
                    dia=dia
                ).first()

                # 2. CREAR (Insert): Aquí es donde fallaba tu error INSERT
                if not menu_dia:
                    menu_dia = MenuSemanal(
                        user_id=current_user.id,
                        week_start=current_week, # <--- CORREGIDO: Objeto date puro
                        dia=dia
                    )
                    db.session.add(menu_dia)
                    db.session.commit()

                # B. Limpiar selecciones previas (CORREGIDO: usa menu_id)
                MenuSelection.query.filter_by(menu_id=menu_dia.id).delete()
                
                # C. Guardar las nuevas selecciones
                for tipo in tipos_comida:
                    # -- RECETAS --
                    recetas_ids = request.form.getlist(f"{dia}_{tipo}_receta")
                    for r_id in recetas_ids:
                        if r_id and r_id != "":
                            sel = MenuSelection(
                                menu_id=menu_dia.id,    # Corregido
                                tipo_comida=tipo,       # Corregido
                                receta_id=int(r_id)
                            )
                            db.session.add(sel)

                    # -- INGREDIENTES SUELTOS --
                    ing_ids = request.form.getlist(f"{dia}_{tipo}_ing_id")
                    ing_qtys = request.form.getlist(f"{dia}_{tipo}_ing_qty")
                    
                    for i_id, i_qty in zip(ing_ids, ing_qtys):
                        if i_id and i_id != "":
                            cantidad = float(i_qty) if i_qty else 0
                            sel = MenuSelection(
                                menu_id=menu_dia.id,    # Corregido
                                tipo_comida=tipo,       # Corregido
                                ingredient_id=int(i_id),
                                quantity=cantidad
                            )
                            db.session.add(sel)

            db.session.commit()
            flash('Menú guardado correctamente.', 'success')
            return redirect(url_for('menu_semanal_page', week_str=current_week))

        except Exception as e:
            db.session.rollback()
            print(f"Error guardando menú: {e}")
            flash(f'Error al guardar: {e}', 'error')

    # -----------------------------------------------------------
    # 3. Preparación de Datos (GET)
    # -----------------------------------------------------------
    menu = []
    
    # Usamos enumerate para calcular la fecha exacta de cada día
    for i, dia in enumerate(dias_semana):
        
        # 1. Obtener datos de la DB
        dia_db = MenuSemanal.query.filter_by(
            user_id=current_user.id, 
            week_start=current_week.strftime('%Y-%m-%d'),
            dia=dia
        ).first()

        # 2. Calcular la fecha visual (ej: 12/05)
        fecha_real = current_week + timedelta(days=i)
        fecha_formateada = fecha_real.strftime('%d/%m')

        if dia_db:
            dia_db.fecha_str = fecha_formateada # Inyectamos la fecha
            menu.append(dia_db)
        else:
            # Objeto dummy para días vacíos
            dummy = MenuSemanal(
                user_id=current_user.id,
                week_start=current_week.strftime('%Y-%m-%d'),
                dia=dia
            )
            dummy.fecha_str = fecha_formateada # Inyectamos la fecha
            menu.append(dummy)

    # Generar lista de compra y cargar catálogos
    lista_compra = generar_lista_compra_db(menu)
    recetas = Receta.query.order_by(Receta.title).all()
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    # Navegación
    prev_week = (current_week - timedelta(weeks=1)).strftime('%Y-%m-%d')
    next_week = (current_week + timedelta(weeks=1)).strftime('%Y-%m-%d')

    return render_template('food/menu.html',
                           current_week=current_week,
                           real_current_week=real_current_week,
                           prev_week=prev_week,
                           next_week=next_week,
                           menu=menu,
                           recetas=recetas,
                           all_ingredients=all_ingredients,
                           lista_compra=lista_compra
                           )


def generar_lista_compra_db(menu_items):
    compra = {}
    tipos = ['Desayuno', 'Comida', 'Merienda', 'Cena']

    for item in menu_items:
        for tipo in tipos:
            # Usamos el nuevo método get_selections que devuelve todo
            selecciones = item.get_selections(tipo)
            
            for sel in selecciones:
                # CASO A: Es Receta
                if sel.receta:
                    for assoc in sel.receta.ingredients_assoc:
                        key = (assoc.ingredient.name, "g")
                        compra[key] = compra.get(key, 0) + assoc.quantity_g
                
                # CASO B: Es Ingrediente Suelto
                elif sel.ingredient:
                    key = (sel.ingredient.name, "g")
                    compra[key] = compra.get(key, 0) + sel.quantity

    resultado = []
    for (nombre, unidad), cantidad in sorted(compra.items()):
        resultado.append({'nombre': nombre, 'unidad': unidad, 'cantidad': round(cantidad, 1)})
    return resultado


@app.route('/shopping_list')
@login_required
def shopping_list():
    # Obtener items ordenados: primero los NO completados, luego los completados
    items = ShoppingItem.query.filter_by(user_id=current_user.id).order_by(ShoppingItem.completed, ShoppingItem.nombre).all()
    return render_template('food/shopping_list.html', items=items)

@app.route('/shopping_list/add', methods=['POST'])
@login_required
def add_shopping_item():
    nombre = request.form.get('nombre')
    if nombre:
        # Añadir item manual
        item = ShoppingItem(nombre=nombre, is_auto=False, user_id=current_user.id)
        db.session.add(item)
        db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/shopping_list/toggle/<int:item_id>')
@login_required
def toggle_shopping_item(item_id):
    item = ShoppingItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item.completed = not item.completed
        db.session.commit()
    return redirect(url_for('shopping_list'))

@app.route('/shopping_list/clear')
@login_required
def clear_completed_items():
    # Borrar solo los que están completados
    ShoppingItem.query.filter_by(user_id=current_user.id, completed=True).delete()
    db.session.commit()
    return redirect(url_for('shopping_list'))


@app.route('/ingredients/edit/<int:id>', methods=['POST'])
@login_required
def edit_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    
    try:
        ing.name = request.form.get('name')
        ing.kcal_100g = float(request.form.get('kcal'))
        ing.price_kg = float(request.form.get('price_kg'))
        
        db.session.commit()
        flash('Ingrediente actualizado correctamente.', 'success')
    except ValueError:
        flash('Error en los datos numéricos.', 'error')
    except Exception as e:
        flash(f'Error al actualizar: {e}', 'error')

    return redirect(url_for('ingredients_manager'))

@app.route('/ingredients/delete/<int:id>')
@login_required
def delete_ingredient(id):
    ing = Ingredient.query.get_or_404(id)
    
    # Verificamos si se usa en recetas para advertir (opcional, por ahora borramos)
    # Gracias al cascade de SQLAlchemy en models.py, se borrará de las recetas automáticamente
    try:
        db.session.delete(ing)
        db.session.commit()
        flash('Ingrediente eliminado del inventario.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('ingredients_manager'))

@app.route('/delete_recipe/<int:id>')
@login_required
def delete_recipe(id):
    receta = Receta.query.get_or_404(id)
    if receta.user_id != current_user.id:
        flash('No tienes permiso para borrar esto.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        db.session.delete(receta)
        db.session.commit()
        flash('Receta eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('recetas_page')) # Asegúrate que la función de la lista se llama recetas_page o index


@app.route('/edit_recipe/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(id):
    receta = Receta.query.get_or_404(id)
    if receta.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('dashboard'))
    
    # Cargamos ingredientes para el desplegable
    all_ingredients = Ingredient.query.order_by(Ingredient.name).all()

    if request.method == 'POST':
        # 1. Actualizar datos básicos
        receta.title = request.form.get('title')
        receta.description = request.form.get('description')
        receta.steps = request.form.get('steps')

        # 2. Actualizar Ingredientes
        # Primero borramos los antiguos (es más fácil que comparar uno a uno)
        # Nota: Al borrar la relación, NO borramos el ingrediente del inventario, solo el vínculo
        for assoc in receta.ingredients_assoc:
            db.session.delete(assoc)
        
        # Ahora creamos los nuevos vínculos desde el JSON
        ing_data_json = request.form.get('ingredients_data')
        if ing_data_json:
            try:
                items = json.loads(ing_data_json)
                for item in items:
                    assoc = RecipeIngredient(
                        recipe_id=receta.id,
                        ingredient_id=int(item['id']),
                        quantity_g=float(item['qty'])
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(f"Error: {e}")

        db.session.commit()
        flash('Receta actualizada.', 'success')
        return redirect(url_for('recetas_page')) # O index/dashboard

    # --- MODO GET: PREPARAR DATOS PARA EL FRONTEND ---
    # Convertimos los ingredientes actuales a un formato que el JavaScript entienda
    preloaded_ingredients = []
    for assoc in receta.ingredients_assoc:
        # Replicamos el cálculo para que el JS no se vuelva loco
        real_kcal = (assoc.quantity_g / 100) * assoc.ingredient.kcal_100g
        real_price = (assoc.quantity_g / 1000) * assoc.ingredient.price_kg
        
        preloaded_ingredients.append({
            'id': str(assoc.ingredient_id), # ID como string para que coincida con el value del select
            'name': assoc.ingredient.name,
            'qty': assoc.quantity_g,
            'realKcal': real_kcal,
            'realPrice': real_price
        })

    # Convertimos a JSON string para inyectarlo en el HTML
    preloaded_json = json.dumps(preloaded_ingredients)

    # Reutilizamos la plantilla create_recipe.html pero pasándole datos extra
    return render_template('food/create_recipe.html', 
                           ingredients=all_ingredients, 
                           receta_editar=receta, # Objeto receta
                           preloaded_json=preloaded_json) # JSON para JS

@app.route('/gym')
@login_required
def gym_dashboard():
    # 1. Sesiones recientes
    recent_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date.desc()).limit(5).all()
    
    # 2. Ejercicios (para el contador del catálogo)
    exercises = Exercise.query.all()

    # 3. RUTINAS (¡NUEVO! Añadimos esto)
    routines = Routine.query.all()
    
    # Pasamos 'routines' a la plantilla
    return render_template('gym/gymdashboard.html', sessions=recent_sessions, exercises=exercises, routines=routines)


@app.route('/gym/exercises', methods=['GET', 'POST'])
@login_required
def gym_exercises():
    form = ExerciseForm()
    if form.validate_on_submit():
        new_ex = Exercise(
            name=form.name.data,
            muscle_group=form.muscle_group.data,
            # --- NUEVOS CAMPOS ---
            description=form.description.data,
            video_link=form.video_link.data,
            burn_rate=form.burn_rate.data,
            # ---------------------
            user_id=current_user.id
        )
        db.session.add(new_ex)
        db.session.commit()
        flash('Ejercicio añadido al catálogo.', 'success')
        return redirect(url_for('gym_exercises'))
    
    exercises = Exercise.query.order_by(Exercise.muscle_group, Exercise.name).all()
    return render_template('gym/exercises.html', form=form, exercises=exercises)
@app.route('/gym/log', methods=['GET', 'POST'])
@login_required
def gym_log():
    exercises = Exercise.query.order_by(Exercise.name).all()
    routines = Routine.query.all()
    
    preloaded_sets = []
    routine_id = request.args.get('routine_id')
    
    if routine_id:
        routine = Routine.query.get(routine_id)
        if routine:
            for ex_assoc in routine.exercises:
                # Determinamos tipo
                is_cardio = (ex_assoc.exercise.muscle_group == 'Cardio')
                
                # --- BUSCAR ÚLTIMO REGISTRO (HISTORIAL) ---
                last_set = WorkoutSet.query.join(WorkoutSession).filter(
                    WorkoutSession.user_id == current_user.id,
                    WorkoutSet.exercise_id == ex_assoc.exercise_id
                ).order_by(WorkoutSession.date.desc()).first()
                
                # Valores por defecto: Prioridad al historial, si no, vacío
                def_weight = last_set.weight if last_set else ''
                def_reps = last_set.reps if last_set else ''
                
                # Para cardio, si no hay historial, miramos si la rutina tenía un objetivo (target)
                def_dist = last_set.distance if (last_set and last_set.distance > 0) else (ex_assoc.target_distance if ex_assoc.target_distance else '')
                def_time = last_set.time if (last_set and last_set.time > 0) else (ex_assoc.target_time if ex_assoc.target_time else '')

                # ------------------------------------------

                preloaded_sets.append({
                    'id': str(ex_assoc.exercise_id),
                    'name': ex_assoc.exercise.name,
                    'type': 'Cardio' if is_cardio else 'Strength',
                    
                    'series': ex_assoc.series if ex_assoc.series else 3,

                    # --- NUEVO: AÑADIMOS INFO PARA EL MODAL DE VIDEO ---
                    'description': ex_assoc.exercise.description or '',
                    'videoLink': ex_assoc.exercise.video_link or '',
                    # ---------------------------------------------------
                    
                    # Usamos los valores históricos aquí
                    'weight': def_weight, 
                    'reps': def_reps,
                    'distance': def_dist,
                    'time': def_time,
                    
                    'rest': ex_assoc.rest_seconds
                })

    if request.method == 'POST':
        data_json = request.form.get('workout_data')
        note = request.form.get('note')
        
        # Procesar FOTO
        photo_file = request.files.get('photo')
        filename = None
        if photo_file and photo_file.filename != '':
            fname = secure_filename(photo_file.filename)
            import time
            fname = f"{int(time.time())}_{fname}"
            photo_file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], fname))
            filename = fname

        if data_json:
            try:
                new_session = WorkoutSession(user_id=current_user.id, note=note, date=datetime.now(), photo_filename=filename)
                db.session.add(new_session)
                db.session.flush()
                
                sets_data = json.loads(data_json)
                
                for index, s in enumerate(sets_data):
                    try:
                        num_series = int(s.get('series', 1))
                    except:
                        num_series = 1
                    
                    has_strength = s.get('weight') and s.get('reps')
                    has_cardio = s.get('distance') or s.get('time')
                    
                    if has_strength or has_cardio:
                        for i in range(num_series):
                            new_set = WorkoutSet(
                                session_id=new_session.id,
                                exercise_id=int(s['id']),
                                order=index, 
                                weight=float(s['weight']) if s.get('weight') else 0,
                                reps=int(s['reps']) if s.get('reps') else 0,
                                distance=float(s['distance']) if s.get('distance') else 0,
                                time=int(s['time']) if s.get('time') else 0
                            )
                            db.session.add(new_set)
                
                db.session.commit()
                flash('Entrenamiento guardado.', 'success')
                return redirect(url_for('gym_dashboard'))
            except Exception as e:
                db.session.rollback()
                print(f"Error: {e}")
                flash('Error al guardar.', 'danger')

    return render_template('gym/log_workout.html', 
                           exercises=exercises, 
                           routines=routines, 
                           preloaded_json=json.dumps(preloaded_sets))

@app.route('/gym/history')
@login_required
def gym_history():
    # Obtener todas las sesiones ordenadas por fecha (más reciente primero)
    sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date.desc()).all()
    return render_template('gym/history.html', sessions=sessions)
@app.route('/gym/session/<int:id>')
@login_required
def gym_session_detail(id):
    session = WorkoutSession.query.get_or_404(id)
    if session.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_history'))
    return render_template('gym/session_detail.html', session=session)

# Asegúrate de importar esto arriba del todo en app.py, o ponlo dentro de la función así:
from itertools import groupby 

@app.route('/gym/measurements/delete/<int:id>')
@login_required
def delete_measurement(id):
    medida = BodyMeasurement.query.get_or_404(id)
    if medida.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_measurements'))
    
    try:
        db.session.delete(medida)
        db.session.commit()
        flash('Registro eliminado.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('gym_measurements'))

@app.route('/gym/measurements/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_measurement(id):
    medida = BodyMeasurement.query.get_or_404(id)
    if medida.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_measurements'))
    
    # Rellenamos el formulario con los datos existentes
    form = BodyMeasurementForm(obj=medida)
    
    if form.validate_on_submit():
        # Actualizamos los campos
        form.populate_obj(medida)
        db.session.commit()
        flash('Medidas actualizadas correctamente.', 'success')
        return redirect(url_for('gym_measurements'))
        
    return render_template('gym/edit_measurement.html', form=form, medida=medida)


@app.route('/gym/progress/<int:exercise_id>')
@login_required
def gym_progress(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    
    # Seguridad: comprobar que el ejercicio es tuyo
    if exercise.user_id != current_user.id:
        flash('No tienes permiso para ver esto.', 'error')
        return redirect(url_for('gym_dashboard'))
    
    # 1. Obtener historial ordenado por fecha (ASCENDENTE para la gráfica)
    history = db.session.query(WorkoutSet, WorkoutSession.date)\
        .join(WorkoutSession)\
        .filter(WorkoutSet.exercise_id == exercise_id)\
        .order_by(WorkoutSession.date.asc())\
        .all()
    
    # 2. Preparar datos para Chart.js
    chart_labels = [] # Eje X: Fechas
    chart_data = []   # Eje Y: Pesos Máximos
    
    # Agrupamos por fecha para sacar el "mejor levantamiento" de cada día
    # (Nota: groupby requiere que los datos ya vengan ordenados, por eso el .order_by de arriba)
    for date_obj, group in groupby(history, key=lambda x: x[1].strftime('%Y-%m-%d')):
        sets_that_day = list(group)
        # Buscamos el peso máximo levantado ese día
        max_weight = max([s[0].weight for s in sets_that_day])
        
        # Formateamos la fecha para que quede bonita en la gráfica (ej: 25 May)
        date_label = datetime.strptime(date_obj, '%Y-%m-%d').strftime('%d %b')
        
        chart_labels.append(date_label)
        chart_data.append(max_weight)
        
    # 3. Renderizar
    # Pasamos 'labels' y 'data' que es lo que pide tu HTML y causaba el error
    return render_template('gym/progress.html', 
                           exercise=exercise, 
                           history=reversed(history), # Invertimos para la tabla (lo más nuevo arriba)
                           labels=chart_labels, 
                           data=chart_data)
    
@app.route('/gym/routines')
@login_required
def gym_routines():
    routines = Routine.query.all()
    return render_template('gym/routines_list.html', routines=routines)


@app.route('/gym/routines/new', methods=['GET', 'POST'])
@login_required
def create_routine():
    form = RoutineForm()
    all_exercises = Exercise.query.order_by(Exercise.name).all()
    
    if request.method == 'POST':
        new_routine = Routine(
            name=request.form.get('name'),
            description=request.form.get('description'),
            user_id=current_user.id
        )
        db.session.add(new_routine)
        db.session.flush()
        
        exercises_json = request.form.get('exercises_data')
        if exercises_json:
            try:
                items = json.loads(exercises_json)
                for i, item in enumerate(items):
                    assoc = RoutineExercise(
                        routine_id=new_routine.id,
                        exercise_id=int(item['id']),
                        order=i,
                        series=int(item.get('series', 1)),
                        rest_seconds=int(item.get('rest', 60)),
                        # Nuevos campos
                        target_distance=float(item.get('distance', 0)),
                        target_time=int(item.get('time', 0))
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(e)
        
        db.session.commit()
        flash('Rutina creada.', 'success')
        return redirect(url_for('gym_routines'))

    return render_template('gym/create_routine.html', form=form, exercises=all_exercises)

@app.route('/gym/measurements', methods=['GET', 'POST'])
@login_required
def gym_measurements():
    form = BodyMeasurementForm()
    
    # --- LOGICA DE GUARDADO (POST) ---
    if form.validate_on_submit():
        # 1. Recuperar la última medición existente para rellenar huecos
        last_measurement = BodyMeasurement.query.filter_by(user_id=current_user.id)\
                                                .order_by(BodyMeasurement.date.desc())\
                                                .first()

        # Lista de campos que queremos revisar
        campos = ['weight', 'biceps', 'chest', 'hips', 'thigh', 'calf']
        datos_para_guardar = {}
        
        algun_dato_nuevo = False

        for campo in campos:
            # Valor que viene del formulario
            valor_form = getattr(form, campo).data
            
            # Si el usuario escribió algo (y no es None)
            if valor_form is not None:
                datos_para_guardar[campo] = valor_form
                algun_dato_nuevo = True
            else:
                # Si el campo está vacío, intentamos coger el valor anterior
                if last_measurement:
                    valor_anterior = getattr(last_measurement, campo)
                    datos_para_guardar[campo] = valor_anterior
                else:
                    # Si no hay historial ni dato nuevo, se queda en None
                    datos_para_guardar[campo] = None

        # Verificamos si realmente vamos a guardar algo útil
        # (al menos un dato nuevo o heredado, para no crear registros vacíos)
        if any(datos_para_guardar.values()) and algun_dato_nuevo:
            try:
                new_entry = BodyMeasurement(
                    user_id=current_user.id,
                    date=datetime.now(),
                    weight=datos_para_guardar['weight'],
                    biceps=datos_para_guardar['biceps'],
                    chest=datos_para_guardar['chest'],
                    hips=datos_para_guardar['hips'],
                    thigh=datos_para_guardar['thigh'],
                    calf=datos_para_guardar['calf']
                )
                db.session.add(new_entry)
                db.session.commit()
                flash('Medidas actualizadas (valores vacíos heredados del anterior).', 'success')
                return redirect(url_for('gym_measurements'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al guardar en BD: {e}', 'error')
        else:
            flash('Introduce al menos un valor nuevo.', 'warning')

    # --- DEPURACIÓN DE ERRORES DE FORMULARIO ---
    elif request.method == 'POST':
        # Esto te dirá exactamente por qué falla si pones decimales y no lo acepta
        flash(f'Error de validación: {form.errors}', 'error')
        print(f"Errores del formulario: {form.errors}")

    # --- PREPARAR DATOS PARA LA GRÁFICA Y TABLA (GET) ---
    # Obtenemos historial ordenado por fecha (ASC para la gráfica)
    history = BodyMeasurement.query.filter_by(user_id=current_user.id).order_by(BodyMeasurement.date.asc()).all()
    
    # FUNCION AUXILIAR: Convierte 0 o None en None para que Chart.js lo ignore
    def clean_val(val):
        return val if (val and val > 0) else None

    # Creamos el diccionario aplicando la limpieza
    chart_data = {
        'labels': [m.date.strftime('%d/%m/%Y') for m in history],
        'weight': [clean_val(m.weight) for m in history],
        'biceps': [clean_val(m.biceps) for m in history],
        'chest':  [clean_val(m.chest) for m in history],
        'hips':   [clean_val(m.hips) for m in history],
        'thigh':  [clean_val(m.thigh) for m in history],
        'calf':   [clean_val(m.calf) for m in history]
    }

    # Invertimos historial para la tabla visual (lo más nuevo arriba)
    return render_template('gym/measurements.html', 
                           form=form, 
                           history=reversed(history),
                           chart_data=json.dumps(chart_data))
# --- GESTIÓN DE EJERCICIOS (EDITAR / BORRAR) ---

@app.route('/gym/exercises/delete/<int:id>')
@login_required
def delete_exercise(id):
    ex = Exercise.query.get_or_404(id)
    if ex.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_exercises'))
    
    # Al borrar el ejercicio, Cascade borrará sus registros en rutinas y logs si está configurado,
    # si no, SQLAlchemy suele manejarlo si las FK están bien.
    try:
        db.session.delete(ex)
        db.session.commit()
        flash('Ejercicio eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar (puede estar en uso): {e}', 'error')
        
    return redirect(url_for('gym_exercises'))

@app.route('/gym/exercises/edit/<int:id>', methods=['POST'])
@login_required
def edit_exercise(id):
    ex = Exercise.query.get_or_404(id)
    if ex.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_exercises'))
    
    ex.name = request.form.get('name')
    ex.muscle_group = request.form.get('muscle_group')
    
    # --- NUEVOS CAMPOS ---
    ex.description = request.form.get('description')
    ex.video_link = request.form.get('video_link')
    try:
        rate = request.form.get('burn_rate')
        ex.burn_rate = float(rate) if rate else 0.0
    except:
        ex.burn_rate = 0.0
    # ---------------------

    db.session.commit()
    flash('Ejercicio actualizado.', 'success')
    return redirect(url_for('gym_exercises'))


# --- GESTIÓN DE RUTINAS (CREAR / EDITAR / BORRAR) ---

@app.route('/gym/routines/delete/<int:id>')
@login_required
def delete_routine(id):
    rutina = Routine.query.get_or_404(id)
    if rutina.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_routines'))
    
    try:
        db.session.delete(rutina)
        db.session.commit()
        flash('Rutina eliminada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}', 'error')
        
    return redirect(url_for('gym_routines'))

@app.route('/gym/routines/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_routine(id):
    rutina = Routine.query.get_or_404(id)
    if rutina.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_routines'))

    all_exercises = Exercise.query.filter_by(user_id=current_user.id).order_by(Exercise.name).all()
    form = RoutineForm(obj=rutina) # Rellena el form con datos actuales

    if request.method == 'POST':
        rutina.name = request.form.get('name')
        rutina.description = request.form.get('description')
        
        # Actualizar ejercicios: Borramos los viejos y creamos los nuevos
        for old_assoc in rutina.exercises:
            db.session.delete(old_assoc)
        
        exercises_json = request.form.get('exercises_data')
        if exercises_json:
            try:
                items = json.loads(exercises_json)
                for i, item in enumerate(items):
                    assoc = RoutineExercise(
                        routine_id=rutina.id,
                        exercise_id=int(item['id']),
                        order=i,
                        series=int(item.get('series', 3)),      # <--- NUEVO
                        rest_seconds=int(item.get('rest', 60))  # <--- NUEVO
                    )
                    db.session.add(assoc)
            except Exception as e:
                print(f"Error JSON: {e}")
        
        db.session.commit()
        flash('Rutina actualizada correctamente.', 'success')
        return redirect(url_for('gym_routines'))

    # PREPARAR DATOS PARA EL FRONTEND (Pre-carga)
    preloaded_data = []
    for assoc in rutina.exercises:
        preloaded_data.append({
            'id': str(assoc.exercise_id),
            'name': assoc.exercise.name,
            'series': assoc.series,          # <--- NUEVO
            'rest': assoc.rest_seconds       # <--- NUEVO
        })
    
    return render_template('gym/create_routine.html', 
                           form=form, 
                           exercises=all_exercises,
                           rutina_editar=rutina,
                           preloaded_json=json.dumps(preloaded_data))

@app.route('/gym/session/delete/<int:id>')
@login_required
def delete_workout_session(id):
    session = WorkoutSession.query.get_or_404(id)
    if session.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_history'))
    
    # 1. Borrar archivo de foto si existe
    if session.photo_filename:
        try:
            file_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], session.photo_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error borrando archivo: {e}")

    # 2. Borrar registro (los sets se borran solos por cascade)
    db.session.delete(session)
    db.session.commit()
    flash('Sesión eliminada correctamente.', 'success')
    return redirect(url_for('gym_history'))

@app.route('/gym/session/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_workout_session(id):
    session = WorkoutSession.query.get_or_404(id)
    if session.user_id != current_user.id:
        flash('No tienes permiso.', 'error')
        return redirect(url_for('gym_history'))

    if request.method == 'POST':
        # Actualizar Nota
        session.note = request.form.get('note')
        
        # Actualizar Fecha (Opcional)
        date_str = request.form.get('date')
        if date_str:
            try:
                # El input datetime-local envía formato 'YYYY-MM-DDTHH:MM'
                session.date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass # Si falla, mantenemos la anterior

        # --- GESTIÓN DE FOTO (Añadir o Cambiar) ---
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename != '':
            # 1. Borrar foto vieja si tenía
            if session.photo_filename:
                try:
                    old_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], session.photo_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except:
                    pass
            
            # 2. Guardar nueva
            fname = secure_filename(photo_file.filename)
            import time
            fname = f"{int(time.time())}_{fname}" # Timestamp único
            photo_file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], fname))
            session.photo_filename = fname
            
        db.session.commit()
        flash('Sesión actualizada.', 'success')
        return redirect(url_for('gym_session_detail', id=session.id))

    return render_template('gym/edit_session.html', session=session)


def update_db_schema(app):
    with app.app_context():
        inspector = inspect(db.engine)
        for table_name, table_obj in db.metadata.tables.items():
            if not inspector.has_table(table_name): continue 
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            
            for column in table_obj.columns:
                if column.name not in existing_columns:
                    print(f"🛠 Añadiendo columna '{column.name}' a '{table_name}'...")
                    col_type = column.type.compile(db.engine.dialect)
                    # Truco: Si es NOT NULL, SQLite da problemas al añadir. Lo hacemos NULLABLE o con DEFAULT.
                    sql = text(f'ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} DEFAULT 0')
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(sql)
                            conn.commit()
                    except Exception as e:
                        print(f"Error: {e}")


@app.route('/admin/users')
@login_required
def admin_users():
    # Seguridad: Si no es admin, fuera
    if not current_user.is_admin:
        flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# 2. ELIMINAR USUARIO
@app.route('/admin/users/delete/<int:id>')
@login_required
def delete_user(id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    if id == current_user.id:
        flash('No puedes eliminar tu propia cuenta desde aquí.', 'warning')
        return redirect(url_for('admin_users'))

    user = User.query.get_or_404(id)
    try:
        # Al borrar el usuario, SQL Alchemy borrará sus recetas, entrenos, etc
        # gracias a los cascade o foreign keys.
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.username} eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {e}', 'error')
        
    return redirect(url_for('admin_users'))

# 3. CAMBIAR ROL (Hacer Admin o quitar Admin)
@app.route('/admin/users/toggle_role/<int:id>')
@login_required
def toggle_admin_role(id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    if id == current_user.id:
        flash('No puedes quitarte el rol de admin a ti mismo.', 'warning')
        return redirect(url_for('admin_users'))

    user = User.query.get_or_404(id)
    user.is_admin = not user.is_admin # Invertir valor
    db.session.commit()
    
    estado = "Administrador" if user.is_admin else "Usuario normal"
    flash(f'Rol actualizado. {user.username} ahora es {estado}.', 'success')
    return redirect(url_for('admin_users'))

# --- RUTA SECRETA PARA CREAR EL PRIMER ADMIN ---
# (Úsala una vez y luego borra este bloque o coméntalo)
@app.route('/setup/make_me_admin')
@login_required
def make_me_admin():
    current_user.is_admin = True
    db.session.commit()
    flash('¡Ahora eres Administrador!', 'success')
    return redirect(url_for('dashboard'))


# En app.py



# --- RUTA CREAR USUARIO (ADMIN) ---
@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def create_user_admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    form = UserAdminForm()
    if form.validate_on_submit():
        # Verificar duplicados
        if User.query.filter_by(username=form.username.data).first():
            flash('El nombre de usuario ya existe.', 'warning')
            return render_template('admin/edit_user.html', form=form, title="Crear Usuario")

        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        
        # Datos físicos
        user.age = form.age.data
        user.height = form.height.data
        user.weight = form.weight.data
        user.gender = form.gender.data
        user.target_weight = form.target_weight.data
        
        # Contraseña obligatoria al crear
        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('La contraseña es obligatoria para nuevos usuarios.', 'error')
            return render_template('admin/edit_user.html', form=form, title="Crear Usuario")

        # Calcular Metabolismo
        user.calculate_bmr()
        
        db.session.add(user)
        db.session.commit()
        flash('Usuario creado correctamente.', 'success')
        return redirect(url_for('admin_users'))
        
    return render_template('admin/edit_user.html', form=form, title="Crear Usuario")

# --- RUTA EDITAR USUARIO (ADMIN) ---
@app.route('/admin/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user_admin(id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
        
    user = User.query.get_or_404(id)
    form = UserAdminForm(obj=user) # Carga datos existentes
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        
        # Datos físicos
        user.age = form.age.data
        user.height = form.height.data
        user.weight = form.weight.data
        user.gender = form.gender.data
        user.target_weight = form.target_weight.data
        
        # Solo cambiamos contraseña si escribieron algo
        if form.password.data:
            user.set_password(form.password.data)
            
        # Recalcular Metabolismo
        user.calculate_bmr()
        
        try:
            db.session.commit()
            flash('Usuario actualizado.', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {e}', 'error')
            
    return render_template('admin/edit_user.html', form=form, title="Editar Usuario", user_bmr=user.basal_metabolism)

# --- EJECUCIÓN ---
if __name__ == '__main__':
    # 1. Crear tablas que no existan (comportamiento normal)
    with app.app_context():
        db.create_all()
        
    # 2. EJECUTAR EL CORRECTOR DINÁMICO (Tu nueva función)
    print("Iniciando chequeo de base de datos...")
    update_db_schema(app)
    
    # 3. Arrancar servidor
    print("Iniciando Home OS Multi-User en puerto 5003...")
    app.run(debug=True, port=5003)