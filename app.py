from flask import Flask, render_template, url_for, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Usuario", "class": "input-field"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Clave", "class": "input-field"})
    submit = SubmitField('Registrarse', render_kw={"class": "submit-button"})

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError('El usuario que elegiste ya existe. Por favor, escoge otro.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Usuario", "class": "input-field"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Clave", "class": "input-field"})
    submit = SubmitField('Entrar', render_kw={"class": "submit-button"})
    
class Turno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    usuario = db.relationship('User', backref=db.backref('turnos', lazy=True))
    opcion = db.Column(db.String(10), nullable=False)
    sitio = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(10))
    fecha_inicio = db.Column(db.DateTime, default=datetime.now)
    fecha_cierre = db.Column(db.DateTime)

    def __repr__(self):
        print(f"Turno(usuario_id={self.usuario_id}, opcion={self.opcion}, sitio={self.sitio}, codigo_postal={self.codigo_postal}, fecha_hora={self.fecha_hora})")
        return f"Turno(usuario_id={self.usuario_id}, opcion={self.opcion}, sitio={self.sitio}, codigo_postal={self.codigo_postal}, fecha_hora={self.fecha_hora})"

class Socio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    captador_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    captador = db.relationship('User', backref=db.backref('socio', lazy=True))
    nombre = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), nullable=False, unique=True)
    fecha_nacimiento = db.Column(db.String(10), nullable=False)  # Cambiado a String
    direccion = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=False)
    horario_llamada = db.Column(db.String(20), nullable=False)
    cuota = db.Column(db.String(5), nullable=False)  # Cambiado a String
    iban = db.Column(db.String(50), nullable=False)



@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html', active_tab= 'dashboard')

@app.route('/ver_turnos', methods=['GET'])
@login_required
def ver_turnos():
    turnos = Turno.query.filter_by(usuario_id=current_user.username).all()
    return render_template('ver_turnos.html', turnos=turnos, active_tab= 'ver_turnos')

def calcular_letra_dni(numeros):
    tabla_letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    return tabla_letras[numeros % 23]

def validar_dni(dni):
    tabla = "TRWAGMYFPDXBNJZSQVHLCKE"
    dig_ext = "XYZ"
    reemp_dig_ext = {'X':'0', 'Y':'1', 'Z':'2'}
    numeros = "1234567890"
    dni = dni.upper()
    if len(dni) == 9:
        dig_control = dni[8]
        dni = dni[:8]
        if dni[0] in dig_ext:
            dni = dni.replace(dni[0], reemp_dig_ext[dni[0]])
        return len(dni) == len([n for n in dni if n in numeros]) \
            and tabla[int(dni)%23] == dig_control
    return False


def validar_iban(iban):
    iban = iban.replace(' ', '').upper()
    if len(iban) != 24 or not iban[:2].isalpha() or not iban[2:].isdigit():
        return False
    iban = iban[4:] + iban[:4]
    iban_numerico = ''.join(str(ord(caracter) - 55) if caracter.isalpha() else caracter for caracter in iban)
    resto = int(iban_numerico) % 97
    return resto == 1
    

@app.route('/altasocios', methods=['GET','POST'])
@login_required
def altasocios():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        dni = request.form['dni']
        fecha_nacimiento = request.form['fecha_nacimiento']
        direccion = request.form['direccion']
        email = request.form['email']
        telefono = request.form['telefono']
        horario_llamada = request.form['horario_llamada']
        cuota = ','.join(request.form.getlist('cuota[]'))
        # Obtener la cuota seleccionada
        otra_cuota = request.form.get('otra_cuota_input')  # Obtener la cuota personalizada
        
        # Verificar si se seleccionó una cuota fija o se ingresó una cuota personalizada
        if otra_cuota:
            cuota = otra_cuota
        iban = request.form['iban']
        
         # Validar el DNI/NIE y el IBAN
        if not validar_dni(dni):
            return "El DNI/NIE ingresado no es válido."
        if not validar_iban(iban):
            return "El IBAN ingresado no es válido."

        nuevo_socio = Socio(captador_id = current_user.username, nombre=nombre, apellidos=apellidos, dni=dni, fecha_nacimiento=fecha_nacimiento, direccion=direccion, email=email, telefono=telefono, horario_llamada=horario_llamada, cuota=cuota, iban=iban)

        db.session.add(nuevo_socio)
        db.session.commit()

        # Redireccionar a una página de confirmación o a otra vista
        return redirect(url_for('altaconfirmada'))

    else:
        return render_template('altasocios.html', active_tab= 'altasocios')

@app.route('/altaconfirmada', methods=['POST', 'GET'])
@login_required
def altaconfirmada():
    return render_template('altaconfirmada.html')
    
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/socioscaptados', methods = ['GET', 'POST'])
@login_required
def socioscaptados():
    socios = Socio.query.filter_by(captador_id=current_user.username).all()
    return render_template('socioscaptados.html', socios=socios, active_tab= 'socioscaptados')

@app.route('/fichar_turno', methods=['GET', 'POST'])
@login_required
def fichar_turno():
    if request.method == 'POST':
        opcion = request.form['opcion']
        if opcion == 'permiso':
            fecha_inicio = datetime.now()
            fecha_cierre = fecha_inicio + timedelta(hours=4)
            sitio = request.form['sitio']
            turno = Turno(usuario_id=current_user.username, opcion=opcion, sitio=sitio, fecha_inicio=fecha_inicio, fecha_cierre=fecha_cierre)
        elif opcion == 'calle':
            fecha_inicio = datetime.now()
            fecha_cierre = fecha_inicio + timedelta(hours=4)
            codigo_postal = request.form['codigo_postal']
            turno = Turno(usuario_id=current_user.username, opcion=opcion,codigo_postal=codigo_postal, fecha_inicio=fecha_inicio, fecha_cierre=fecha_cierre)
        
        # Guarda el turno en la base de datos
        db.session.add(turno)
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    else:
        return render_template('fichar_turno.html', active_tab= 'fichar_turno')
    
@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Obtener el puerto de la variable de entorno $PORT
    app.run(host='0.0.0.0', port=port, debug=True)
